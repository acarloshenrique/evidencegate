import { test } from 'node:test';
import assert from 'node:assert/strict';
import { VoiceSession, streamChat } from '../app/web/voice-session.mjs';

const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const ok = data => ({ ok: true, json: async () => ({ code: 0, data }) });

function harness() {
  const events = [], statuses = [];
  const track = { readyState: 'live', stop: () => events.push('track.stop') };
  const stream = { getTracks: () => [track], getAudioTracks: () => [track] };
  const rtc = { on() {}, removeAllListeners() {},
    join: async () => { events.push('join'); },
    publish: async () => { events.push('publish'); },
    leave: async () => { events.push('leave'); } };
  const mediaDevices = {
    getUserMedia: async constraints => {
      events.push('getUserMedia'); assert.deepEqual(constraints, { audio: true, video: false });
      return stream;
    },
    enumerateDevices: async () => { events.push('enumerate'); return [{ kind: 'audioinput' }]; },
  };
  const sdk = {
    createCustomAudioTrack: ({ mediaStreamTrack }) => {
      assert.equal(mediaStreamTrack, track);
      events.push('customTrack'); return { close: () => events.push('mic.close') };
    },
    createClient: () => { events.push('createClient'); return rtc; },
  };
  const fetcher = async path => {
    events.push(path);
    return ok(path === '/voice/config' ? { app_id: 'app', channel_name: 'channel',
      uid: 1, agent_uid: 2, token: 'test' } : { agent_id: 'agent' });
  };
  const args = { mediaDevices, sdk, fetcher, timeout: 100,
    status: (...values) => statuses.push(values) };
  return { events, statuses, rtc, mediaDevices, args, stream };
}

test('missing microphone: no configuration, RTC channel or server agent', async () => {
  const h = harness();
  h.mediaDevices.getUserMedia = async () => { throw Object.assign(new Error('missing'), { name: 'NotFoundError' }); };
  const voice = new VoiceSession(h.args);
  assert.equal(await voice.start(), false);
  assert.equal(h.events.length, 0);
  assert.match(h.statuses.at(-1)[1], /Nenhum microfone/);
  assert.equal(voice.current, null);
});

test('permission denial and empty audioinput both stop before channel creation', async () => {
  for (const denial of [true, false]) {
    const h = harness();
    if (denial) h.mediaDevices.getUserMedia = async () => { throw { name: 'NotAllowedError' }; };
    else h.mediaDevices.enumerateDevices = async () => [];
    assert.equal(await new VoiceSession(h.args).start(), false);
    assert(!h.events.includes('/voice/config'));
    if (!denial) assert(h.events.includes('track.stop'));
  }
});

test('permission precedes enumeration and channel; retry and stop clean all resources', async () => {
  const h = harness(); const voice = new VoiceSession(h.args);
  assert.equal(await voice.start(), true);
  assert.deepEqual(h.events.slice(0, 4), ['getUserMedia', 'enumerate', 'customTrack', '/voice/config']);
  await voice.stop();
  for (const event of ['track.stop', 'mic.close', 'leave', '/voice/stop']) assert(h.events.includes(event));
  assert.equal(await voice.start(), true);
  await voice.stop();
  assert.equal(h.events.filter(x => x === '/voice/start').length, 2);
});

test('double click cannot create duplicate channels', async () => {
  const h = harness(); const voice = new VoiceSession(h.args);
  const first = voice.start();
  assert.equal(await voice.start(), false);
  assert.equal(await first, true);
  assert.equal(h.events.filter(x => x === 'createClient').length, 1);
  await voice.stop();
});

test('publish failure closes the track and client before retry', async () => {
  const h = harness();
  h.rtc.publish = async () => { throw new Error('publish failed'); };
  const voice = new VoiceSession(h.args);
  assert.equal(await voice.start(), false);
  assert(h.events.includes('mic.close') && h.events.includes('leave'));
  assert(!h.events.includes('/voice/start'));
  assert.equal(voice.current, null);
});

test('late permission resolution after timeout immediately stops captured track', async () => {
  const h = harness();
  h.args.timeout = 5;
  h.mediaDevices.getUserMedia = async () => { await delay(20); return h.stream; };
  assert.equal(await new VoiceSession(h.args).start(), false);
  await delay(30);
  assert(h.events.includes('track.stop'));
  assert(!h.events.includes('createClient'));
});

test('late server-agent start after timeout is stopped', async () => {
  const h = harness(); const fetcher = h.args.fetcher;
  h.args.timeout = 5;
  h.args.fetcher = async path => {
    if (path === '/voice/start') await delay(20);
    return fetcher(path);
  };
  assert.equal(await new VoiceSession(h.args).start(), false);
  await delay(30);
  assert(h.events.includes('/voice/stop'));
});

test('text-mode cancellation during microphone acquisition stops late capture', async () => {
  const h = harness();
  h.mediaDevices.getUserMedia = async () => { await delay(10); return h.stream; };
  const voice = new VoiceSession(h.args);
  const start = voice.start();
  await voice.stop();
  assert.equal(await start, false);
  assert(h.events.includes('track.stop'));
  assert(!h.events.includes('createClient'));
});

test('unconfirmed remote stop prevents creating another server agent', async () => {
  const h = harness(); const fetcher = h.args.fetcher;
  h.args.fetcher = async path => path === '/voice/stop' ? { ok: false } : fetcher(path);
  const voice = new VoiceSession(h.args);
  assert.equal(await voice.start(), true);
  await voice.stop();
  assert.equal(await voice.start(), false);
  assert.equal(h.events.filter(x => x === '/voice/start').length, 1);
});

test('SSE text fallback reads fragmented UTF-8 without microphone or Agora', async () => {
  const bytes = new TextEncoder().encode('data: {"choices":[{"delta":{"content":"Missão íntegra"}}]}\r\n\r\ndata: [DONE]\n\n');
  let text = '';
  await streamChat('Teve ataque?', delta => { text += delta; }, async (path, options) => {
    assert.equal(path, '/chat/completions');
    assert.equal(JSON.parse(options.body).stream, true);
    return { ok: true, body: new ReadableStream({ start(controller) {
      for (let i = 0; i < bytes.length; i += 2) controller.enqueue(bytes.slice(i, i + 2));
      controller.close();
    } }) };
  });
  assert.equal(text, 'Missão íntegra');
});

test('text fallback reports HTTP errors and truncated streams', async () => {
  await assert.rejects(streamChat('oi', () => {}, async () => ({ ok: false })), /consultar/);
  await assert.rejects(streamChat('oi', () => {}, async () => ({ ok: true,
    body: new ReadableStream({ start(controller) { controller.close(); } }) })), /interrompida/);
});

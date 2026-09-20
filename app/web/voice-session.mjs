// Agora accepts the already-open MediaStreamTrack. No cached deviceId, second
// acquisition or RTC channel is needed to discover that there is no microphone.
export function voiceError(error) {
  const name = error?.name ?? '';
  const message = String(error?.message ?? error);
  if (/NotFound|DevicesNotFound/.test(name) || /DEVICE_NOT_FOUND/.test(message))
    return 'Nenhum microfone encontrado. Conecte um dispositivo e tente novamente, ou use o modo texto.';
  if (/NotAllowed|PermissionDenied|Security/.test(name))
    return 'Permissão do microfone negada. Libere o acesso no navegador ou use o modo texto.';
  if (/NotReadable|TrackStart/.test(name))
    return 'O microfone está ocupado ou indisponível. Feche outros aplicativos ou use o modo texto.';
  return message;
}

function bounded(promise, milliseconds, late = () => {}) {
  return new Promise((resolve, reject) => {
    let expired = false;
    const timer = setTimeout(() => {
      expired = true;
      reject(new Error('Tempo de conexão esgotado. Tente novamente ou use o modo texto.'));
    }, milliseconds);
    Promise.resolve(promise).then(value => {
      clearTimeout(timer);
      if (expired) Promise.resolve(late(value)).catch(() => {});
      else resolve(value);
    }, error => { clearTimeout(timer); if (!expired) reject(error); });
  });
}

export class VoiceSession {
  // Native fetch throws "Illegal invocation" when called as a method of another
  // object (this.fetcher(...)), so the default must be a plain wrapper.
  constructor({ mediaDevices, sdk, fetcher = (...args) => fetch(...args), status = () => {}, timeout = 15000 }) {
    Object.assign(this, { mediaDevices, sdk, fetcher, status, timeout });
    this.current = null;
    this.busy = false;
    this.unconfirmedAgents = new Set();
  }

  async request(path, body) {
    const response = await this.fetcher(path, { method: body ? 'POST' : 'GET',
      headers: { 'Content-Type': 'application/json' },
      ...(body ? { body: JSON.stringify(body) } : {}) });
    if (!response.ok) throw new Error('Serviço de voz indisponível. Use o modo texto.');
    const value = await response.json();
    if (value.code !== undefined && value.code !== 0)
      throw new Error('O servidor de voz não conseguiu concluir a solicitação.');
    return value;
  }

  async stopAgent(id) {
    this.unconfirmedAgents.add(id);
    await bounded(this.request('/voice/stop', { agentId: id }), this.timeout);
    this.unconfirmedAgents.delete(id);
  }

  async cleanup(s) {
    s.cancelled = true;
    s.stream?.getTracks().forEach(track => track.stop());
    try { s.mic?.close(); } catch { /* continue releasing other resources */ }
    s.mic = null;
    s.client?.removeAllListeners();
    const jobs = [];
    if (s.client) jobs.push(bounded(s.client.leave(), this.timeout));
    if (s.agentId) jobs.push(this.stopAgent(s.agentId));
    const outcomes = await Promise.allSettled(jobs);
    if (outcomes.some(outcome => outcome.status === 'rejected'))
      this.status('aviso', 'Áudio local encerrado; encerramento remoto não confirmado.');
  }

  async start() {
    if (this.busy || this.current) return false;
    this.busy = true;
    const s = { cancelled: false };
    this.current = s;
    const check = () => { if (s.cancelled) throw new Error('Conexão cancelada.'); };
    try {
      for (const id of this.unconfirmedAgents) await this.stopAgent(id);
      this.status('conectando', 'Verificando microfone e permissão…');
      if (!this.mediaDevices?.getUserMedia)
        throw new Error('Microfone indisponível neste navegador. Use HTTPS ou o modo texto.');
      s.stream = await bounded(this.mediaDevices.getUserMedia({ audio: true, video: false }),
        this.timeout, stream => stream.getTracks().forEach(track => track.stop()));
      check();
      const devices = await bounded(this.mediaDevices.enumerateDevices(), this.timeout);
      check();
      const raw = s.stream.getAudioTracks()[0];
      if (!devices.some(device => device.kind === 'audioinput') || !raw || raw.readyState === 'ended')
        throw Object.assign(new Error('DEVICE_NOT_FOUND'), { name: 'NotFoundError' });
      const sdk = typeof this.sdk === 'function' ? this.sdk() : this.sdk;
      if (!sdk) throw new Error('SDK de voz indisponível. Use o modo texto.');
      s.mic = sdk.createCustomAudioTrack({ mediaStreamTrack: raw });
      const cfg = (await bounded(this.request('/voice/config'), this.timeout)).data;
      check();
      if (!cfg?.app_id || !cfg.channel_name) throw new Error('Configuração de voz inválida.');
      const uid = Number(cfg.uid), agentUid = Number(cfg.agent_uid);
      if (!Number.isInteger(uid) || !Number.isInteger(agentUid))
        throw new Error('Identificação de voz inválida.');
      s.client = sdk.createClient({ mode: 'rtc', codec: 'vp8' });
      s.client.on('user-published', async (user, type) => {
        try {
          if (s.cancelled) return;
          await s.client.subscribe(user, type);
          if (!s.cancelled && type === 'audio') user.audioTrack.play();
        } catch { if (!s.cancelled) this.status('aviso', 'Não foi possível reproduzir o áudio remoto.'); }
      });
      raw.addEventListener?.('ended', () => {
        if (!s.cancelled) void this.stop().then(() =>
          this.status('erro', 'Microfone desconectado. Tente novamente ou use o modo texto.'));
      }, { once: true });
      this.status('conectando', 'Microfone pronto. Entrando no canal…');
      await bounded(s.client.join(cfg.app_id, cfg.channel_name, cfg.token, uid),
        this.timeout, () => s.client.leave());
      check();
      await bounded(s.client.publish([s.mic]), this.timeout, () => s.client.leave());
      check();
      const result = await bounded(this.request('/voice/start', {
        channelName: cfg.channel_name, rtcUid: agentUid, userUid: uid,
      }), this.timeout, value => value.data?.agent_id && this.stopAgent(value.data.agent_id));
      s.agentId = result.data?.agent_id;
      check();
      if (!s.agentId) throw new Error('O agente de voz não iniciou. Use o modo texto.');
      this.status('AO VIVO', 'Fale agora. O auditor consulta os dados do sistema.', true);
      return true;
    } catch (error) {
      const cancelled = s.cancelled;
      await this.cleanup(s);
      if (this.current === s) this.current = null;
      if (!cancelled) this.status('erro', voiceError(error));
      return false;
    } finally { this.busy = false; }
  }

  async stop() {
    const s = this.current;
    this.current = null;
    if (s) await this.cleanup(s);
  }
}

export async function streamChat(question, onDelta, fetcher = fetch) {
  const response = await fetcher('/chat/completions', { method: 'POST',
    headers: { 'Content-Type': 'application/json' }, signal: AbortSignal.timeout(60000),
    body: JSON.stringify({ stream: true, messages: [{ role: 'user', content: question }] }) });
  if (!response.ok || !response.body)
    throw new Error('Não foi possível consultar o auditor. Confira a conexão e a configuração do serviço.');
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let doneReceived = false;
  try {
    while (!doneReceived) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      let index;
      while ((index = buffer.indexOf('\n')) >= 0) {
        const line = buffer.slice(0, index).trimEnd();
        buffer = buffer.slice(index + 1);
        if (!line.startsWith('data:')) continue;
        const payload = line.slice(5).trim();
        if (payload === '[DONE]') { doneReceived = true; break; }
        if (!payload) continue;
        const content = JSON.parse(payload).choices?.[0]?.delta?.content;
        if (content) onDelta(content);
      }
      if (done) break;
    }
    if (!doneReceived) throw new Error('Resposta interrompida. Tente enviar a pergunta novamente.');
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}

import { VoiceSession, streamChat } from './voice-session.mjs';
const $ = id => document.getElementById(id);
const session = new VoiceSession({ mediaDevices: navigator.mediaDevices, sdk: () => window.AgoraRTC,
  status(title, detail, live = false) {
    $('stt').textContent = title;
    $('sts').textContent = detail;
    $('dot').className = 'dot' + (live ? ' on' : '');
    $('stop').hidden = !live;
    if (title === 'erro') { $('btn').textContent = 'Tentar novamente'; $('btn').disabled = false; }
  } });

$('btn').addEventListener('click', async () => {
  $('btn').disabled = true;
  const connected = await session.start();
  $('btn').disabled = connected || session.busy;
});
$('stop').addEventListener('click', async () => {
  await session.stop();
  $('stt').textContent = 'desconectado';
  $('sts').textContent = 'Sessão encerrada.';
  $('dot').className = 'dot';
  $('stop').hidden = true;
  $('btn').disabled = session.busy;
});
$('text-mode').addEventListener('click', async () => {
  $('text-panel').hidden = false;
  $('question').focus();
  await session.stop();
  $('stop').hidden = true;
  $('btn').disabled = session.busy;
  $('dot').className = 'dot';
  $('stt').textContent = 'modo texto';
  $('sts').textContent = 'Pergunte sobre ameaças, missões ou bloqueios.';
});
$('chat-form').addEventListener('submit', async event => {
  event.preventDefault();
  const question = $('question').value.trim();
  if (!question || $('send').disabled) return;
  $('send').disabled = true;
  $('answer').textContent = '';
  $('chat-error').textContent = '';
  try { await streamChat(question, delta => { $('answer').textContent += delta; }); }
  catch (error) { $('chat-error').textContent = error.message; }
  finally { $('send').disabled = false; }
});
window.addEventListener('pagehide', () => { void session.stop(); });

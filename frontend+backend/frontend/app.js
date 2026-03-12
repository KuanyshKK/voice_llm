const API_BASE = 'http://localhost:8000';

// DOM refs
const orbWrapper   = document.getElementById('orbWrapper');
const orb          = document.getElementById('orb');
const iconMic      = document.getElementById('iconMic');
const iconThinking = document.getElementById('iconThinking');
const iconWave     = document.getElementById('iconWave');
const statusText   = document.getElementById('statusText');
const transcriptArea = document.getElementById('transcriptArea');
const userText     = document.getElementById('userText');
const aiText       = document.getElementById('aiText');

let mediaRecorder = null;
let audioChunks   = [];
let isRecording   = false;
let currentAudio  = null;

// Human-readable labels for each state
const STATUS_LABELS = {
  idle:       'Tap to speak',
  recording:  'Listening...',
  processing: 'Thinking...',
  playing:    'Speaking...',
};

/**
 * Transition the UI to a named state.
 * The state name becomes the only class on orbWrapper (besides "orb-wrapper"),
 * which drives all CSS animations and icon visibility.
 */
function setState(state) {
  orbWrapper.className = 'orb-wrapper ' + state;
  statusText.textContent = STATUS_LABELS[state] ?? state;
}

/**
 * Request microphone access and start recording.
 * Prefers webm/opus; falls back to mp4 for Safari.
 */
async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];

    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : 'audio/mp4';

    mediaRecorder = new MediaRecorder(stream, { mimeType });

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = async () => {
      // Stop all tracks so the browser releases the mic indicator
      stream.getTracks().forEach((t) => t.stop());
      const blob = new Blob(audioChunks, { type: mimeType });
      const ext  = mimeType.includes('mp4') ? 'mp4' : 'webm';
      await sendAudio(blob, ext);
    };

    mediaRecorder.start(100); // collect data every 100 ms
    isRecording = true;
    setState('recording');
  } catch (err) {
    console.error('[startRecording]', err);
    statusText.textContent = 'Microphone access denied';
    setTimeout(() => setState('idle'), 2500);
  }
}

/**
 * Stop the active recording session.
 * The onstop handler fires asynchronously and takes over from here.
 */
function stopRecording() {
  if (mediaRecorder && isRecording) {
    mediaRecorder.stop();
    isRecording = false;
    setState('processing');
  }
}

/**
 * Upload the recorded blob to the backend, display the transcript +
 * AI reply, then play back the synthesised speech audio.
 */
async function sendAudio(blob, ext) {
  try {
    const form = new FormData();
    form.append('audio', blob, `recording.${ext}`);

    const res = await fetch(`${API_BASE}/api/voice`, {
      method: 'POST',
      body: form,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Server error' }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();

    // Populate and reveal the transcript cards
    userText.textContent = data.transcript;
    aiText.textContent   = data.response_text;
    transcriptArea.classList.add('visible');

    // Decode base64 MP3 and create a playable object URL
    const bytes    = Uint8Array.from(atob(data.audio), (c) => c.charCodeAt(0));
    const audioBlob = new Blob([bytes], { type: 'audio/mpeg' });
    const url      = URL.createObjectURL(audioBlob);

    // Stop and clean up any previously playing audio
    if (currentAudio) {
      currentAudio.pause();
      URL.revokeObjectURL(currentAudio.src);
    }

    currentAudio = new Audio(url);
    setState('playing');

    currentAudio.onended = () => {
      URL.revokeObjectURL(url);
      setState('idle');
    };

    currentAudio.onerror = () => setState('idle');

    await currentAudio.play();
  } catch (err) {
    console.error('[sendAudio]', err);
    statusText.textContent = `Error: ${err.message}`;
    setTimeout(() => setState('idle'), 3000);
  }
}

// Click handler: toggle recording; ignore clicks while processing or playing
orb.addEventListener('click', () => {
  if (isRecording) {
    stopRecording();
  } else if (
    !orbWrapper.classList.contains('processing') &&
    !orbWrapper.classList.contains('playing')
  ) {
    startRecording();
  }
});

// Boot the UI
setState('idle');

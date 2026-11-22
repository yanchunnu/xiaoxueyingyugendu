const STORAGE_KEY = "readalong-player-settings";

const audio = new Audio();
let runId = 0;
let paused = false;
let pauseWaiters = [];
let manifestTopics = [];

const $ = (id) => document.getElementById(id);

function loadSettings() {
  const defaults = { wordRepeats: 3, sentenceRepeats: 1, fullRepeats: 1, showKorean: true };
  try {
    return { ...defaults, ...JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}") };
  } catch {
    return defaults;
  }
}

function saveSettings() {
  const settings = {
    wordRepeats: Number($("wordN").value),
    sentenceRepeats: Number($("sentN").value),
    fullRepeats: Number($("fullN").value),
    showKorean: !document.body.classList.contains("hide-ko"),
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}

function applySettings(settings) {
  $("wordN").value = String(settings.wordRepeats);
  $("sentN").value = String(settings.sentenceRepeats);
  $("fullN").value = String(settings.fullRepeats);
  document.body.classList.toggle("hide-ko", !settings.showKorean);
  $("koToggle").textContent = settings.showKorean ? "한국어 뜻 숨기기" : "한국어 뜻 보기";
}

function topicId() {
  const raw = new URLSearchParams(location.search).get("t") || "001";
  const n = String(parseInt(raw, 10)).padStart(3, "0");
  return n === "NaN" ? "001" : n;
}

async function loadTopic() {
  const id = topicId();
  const manifest = await (await fetch("content/manifest.json")).json();
  manifestTopics = manifest.topics;
  const meta = manifest.topics.find((item) => String(item.number).padStart(3, "0") === id);
  if (!meta) throw new Error("주제를 찾을 수 없습니다.");
  const data = await (await fetch(meta.file)).json();
  return { id, meta, data };
}

function render(topic) {
  $("title").textContent = `${topic.meta.number}. ${topic.data.topic}`;
  $("titleKo").textContent = topic.data.topic_ko;
  document.title = `${topic.data.topic} · 따라 읽기`;

  const words = $("words");
  words.innerHTML = "";
  topic.data.words.forEach((word, index) => {
    const div = document.createElement("div");
    div.className = "word";
    div.dataset.index = String(index);
    div.innerHTML = `<div class="en"></div><div class="ko"></div>`;
    div.querySelector(".en").textContent = word.en;
    div.querySelector(".ko").textContent = word.ko;
    words.appendChild(div);
  });

  const list = $("passage");
  list.innerHTML = "";
  topic.data.phrases.forEach((phrase, index) => {
    const li = document.createElement("li");
    li.dataset.index = String(index);
    li.innerHTML = `<div class="en"></div><div class="ko"></div>`;
    li.querySelector(".en").textContent = phrase.en;
    li.querySelector(".ko").textContent = phrase.ko;
    list.appendChild(li);
  });

  const prev = manifestTopics.find((item) => item.number === topic.meta.number - 1);
  const next = manifestTopics.find((item) => item.number === topic.meta.number + 1);
  $("prev").hidden = !prev;
  $("next").hidden = !next;
  if (prev) $("prev").href = `player.html?t=${String(prev.number).padStart(3, "0")}`;
  if (next) $("next").href = `player.html?t=${String(next.number).padStart(3, "0")}`;
}

function clearCurrent() {
  document.querySelectorAll(".current, .current-all").forEach((el) => {
    el.classList.remove("current", "current-all");
  });
}

function mark(selector, index) {
  clearCurrent();
  const el = document.querySelector(`${selector}[data-index="${index}"]`);
  if (el) {
    el.classList.add("current");
    el.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }
}

function waitWhilePaused() {
  if (!paused) return Promise.resolve();
  return new Promise((resolve) => pauseWaiters.push(resolve));
}

function playUrl(url, id) {
  return new Promise((resolve, reject) => {
    const finish = () => {
      audio.onended = null;
      audio.onerror = null;
      resolve(audio.duration || 0);
    };
    audio.onended = finish;
    audio.onerror = () => reject(new Error("음원을 재생할 수 없습니다."));
    audio.src = url;
    audio.play().catch(reject);
    if (id !== runId) reject(new Error("cancelled"));
  });
}

async function gap(seconds, id) {
  let left = Math.max(0, seconds) * 1000;
  while (left > 0) {
    if (id !== runId) return;
    await waitWhilePaused();
    if (id !== runId) return;
    const slice = Math.min(left, 120);
    await new Promise((resolve) => setTimeout(resolve, slice));
    if (!paused) left -= slice;
  }
}

function repeatGap(duration, extra, minimum, fallback) {
  const length = Number.isFinite(duration) ? duration : fallback;
  return Math.max(minimum, length + extra);
}

async function playRepeats(url, times, id, label, extra, minimum, fallback) {
  for (let i = 1; i <= times; i += 1) {
    if (id !== runId) return;
    await waitWhilePaused();
    $("status").textContent = `${label} · ${i} / ${times}`;
    const duration = await playUrl(url, id);
    if (id !== runId) return;
    await gap(repeatGap(duration, extra, minimum, fallback), id);
  }
}

async function run(topic) {
  const id = ++runId;
  paused = false;
  $("play").disabled = true;
  $("pause").disabled = false;
  const wordN = Number($("wordN").value);
  const sentN = Number($("sentN").value);
  const fullN = Number($("fullN").value);
  const base = window.PREVIEW_CLIP_BASE || `audio/clips/${topic.id}`;
  try {
    if (wordN > 0) {
      for (let i = 0; i < topic.data.words.length; i += 1) {
        if (id !== runId) return;
        mark("#words .word", i);
        await playRepeats(`${base}/w${String(i + 1).padStart(2, "0")}.mp3`, wordN, id, `단어 ${i + 1}`, 0.6, 1.2, 0.6);
      }
    }
    if (sentN > 0) {
      for (let i = 0; i < topic.data.phrases.length; i += 1) {
        if (id !== runId) return;
        mark("#passage li", i);
        await playRepeats(`${base}/s${String(i + 1).padStart(2, "0")}.mp3`, sentN, id, `문장 ${i + 1}`, 1.5, 0, 1);
      }
    }
    if (fullN > 0) {
      clearCurrent();
      $("passage").classList.add("current-all");
      await playRepeats(`${base}/full.mp3`, fullN, id, "본문 전체", 1.5, 0, 1);
    }
    if (id === runId) $("status").textContent = "끝났어요. 참 잘했어요!";
  } catch (error) {
    if (id === runId) $("status").textContent = error.message || "재생을 멈췄어요.";
  } finally {
    if (id === runId) {
      $("play").disabled = false;
      $("pause").disabled = true;
      clearCurrent();
      $("passage").classList.remove("current-all");
    }
  }
}

function stop() {
  runId += 1;
  paused = false;
  pauseWaiters.splice(0).forEach((fn) => fn());
  audio.pause();
  $("play").disabled = false;
  $("pause").disabled = true;
  $("status").textContent = "멈췄어요.";
  clearCurrent();
}

async function main() {
  const settings = loadSettings();
  applySettings(settings);
  const topic = window.PREVIEW_TOPIC || await loadTopic();
  render(topic);

  ["wordN", "sentN", "fullN"].forEach((id) => $(id).addEventListener("change", saveSettings));
  $("koToggle").addEventListener("click", () => {
    document.body.classList.toggle("hide-ko");
    $("koToggle").textContent = document.body.classList.contains("hide-ko")
      ? "한국어 뜻 보기"
      : "한국어 뜻 숨기기";
    saveSettings();
  });
  $("play").addEventListener("click", () => {
    saveSettings();
    if (paused) {
      paused = false;
      pauseWaiters.splice(0).forEach((fn) => fn());
      if (audio.src && audio.paused && !audio.ended) audio.play();
      $("play").disabled = true;
      $("pause").disabled = false;
      return;
    }
    run(topic);
  });
  $("pause").addEventListener("click", () => {
    paused = true;
    audio.pause();
    $("pause").disabled = true;
    $("play").disabled = false;
    $("status").textContent = "일시정지";
  });
  $("stop").addEventListener("click", stop);
}

main().catch((error) => {
  $("status").textContent = error.message || "주제를 열 수 없습니다.";
});

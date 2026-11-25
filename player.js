const STORAGE_KEY = "readalong-player-settings";
const LANG_KEY = "readalong-player-lang";
const RATES = [0.6, 0.7, 0.8, 0.9, 1, 1.1, 1.2, 1.3];

const audio = new Audio();
let runId = 0;
let paused = false;
let pauseWaiters = [];
let manifestTopics = [];
let currentLang = "en";
let currentTopic = null;

const $ = (id) => document.getElementById(id);

function nearestRate(value) {
  const rate = Number(value);
  return RATES.find((item) => Math.abs(item - rate) < 0.001) ?? 1;
}

function loadSettings() {
  const defaults = {
    wordRepeats: 3,
    sentenceRepeats: 1,
    fullRepeats: 1,
    showKorean: true,
    showPinyin: true,
    wordRate: 1,
    sentenceRate: 1,
  };
  try {
    const saved = { ...defaults, ...JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}") };
    saved.wordRate = nearestRate(saved.wordRate);
    saved.sentenceRate = nearestRate(saved.sentenceRate);
    return saved;
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
    showPinyin: !document.body.classList.contains("hide-py"),
    wordRate: nearestRate($("wordRate").value),
    sentenceRate: nearestRate($("sentRate").value),
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}

function applySettings(settings) {
  $("wordN").value = String(settings.wordRepeats);
  $("sentN").value = String(settings.sentenceRepeats);
  $("fullN").value = String(settings.fullRepeats);
  $("wordRate").value = String(settings.wordRate);
  $("sentRate").value = String(settings.sentenceRate);
  document.body.classList.toggle("hide-ko", !settings.showKorean);
  document.body.classList.toggle("hide-py", !settings.showPinyin);
  $("koToggle").textContent = settings.showKorean ? "한국어 뜻 숨기기" : "한국어 뜻 보기";
  $("pyToggle").textContent = settings.showPinyin ? "拼音 숨기기" : "拼音 보기";
  updateSettingsSummary();
}

function rateLabel(value) {
  return `${nearestRate(value).toFixed(1)}x`;
}

function updateSettingsSummary() {
  const summary = $("settingsSummary");
  if (!summary || !$("wordN")) return;
  const lang = currentLang === "zh" ? "中文" : "English";
  summary.textContent = `${lang} · 단어 ${$("wordN").value}회 ${rateLabel($("wordRate").value)} · 문장 ${$("sentN").value}회 ${rateLabel($("sentRate").value)}`;
}

function syncBarHeight() {
  const bar = $("controls");
  if (!bar) return;
  document.documentElement.style.setProperty("--bar-h", `${bar.offsetHeight}px`);
}

function setSettingsOpen(open) {
  const panelOpen = Boolean(open);
  $("controls").classList.toggle("collapsed", !panelOpen);
  $("settingsToggle").setAttribute("aria-expanded", panelOpen ? "true" : "false");
  updateSettingsSummary();
  requestAnimationFrame(syncBarHeight);
}

function initialLang() {
  const query = new URLSearchParams(location.search).get("lang");
  if (query === "zh" || query === "en") return query;
  const saved = localStorage.getItem(LANG_KEY);
  if (saved === "zh" || saved === "en") return saved;
  return "en";
}

function setLang(lang, updateUrl) {
  const next = lang === "zh" ? "zh" : "en";
  const changed = next !== currentLang;
  currentLang = next;
  localStorage.setItem(LANG_KEY, currentLang);
  document.body.classList.toggle("lang-zh", currentLang === "zh");
  $("langEn").setAttribute("aria-pressed", currentLang === "en" ? "true" : "false");
  $("langZh").setAttribute("aria-pressed", currentLang === "zh" ? "true" : "false");
  $("pyToggle").hidden = currentLang !== "zh";
  updateSettingsSummary();
  if (updateUrl) {
    const url = new URL(location.href);
    url.searchParams.set("lang", currentLang);
    history.replaceState(null, "", url);
  }
  if (changed && currentTopic) stop();
  if (currentTopic) render(currentTopic);
}

function topicId() {
  const raw = new URLSearchParams(location.search).get("t") || "001";
  const n = String(parseInt(raw, 10)).padStart(3, "0");
  return n === "NaN" ? "001" : n;
}

function topicHref(number) {
  return `player.html?t=${String(number).padStart(3, "0")}&lang=${currentLang}`;
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

function mainText(item) {
  if (currentLang === "zh") return item.zh || item.en;
  return item.en;
}

function render(topic) {
  const zh = currentLang === "zh";
  const title = zh ? (topic.data.topic_zh || topic.data.topic) : topic.data.topic;
  $("title").textContent = `${topic.meta.number}. ${title}`;
  $("titlePy").textContent = zh ? (topic.data.topic_pinyin || "") : "";
  $("titlePy").hidden = !zh;
  $("titleKo").textContent = topic.data.topic_ko;
  document.title = zh ? `${title} · 中文` : `${topic.data.topic} · 따라 읽기`;
  $("wordsHeading").textContent = zh ? "单词 Words" : "Words 단어";

  const words = $("words");
  words.innerHTML = "";
  topic.data.words.forEach((word, index) => {
    const div = document.createElement("div");
    div.className = "word";
    div.dataset.index = String(index);
    div.innerHTML = `<div class="py"></div><div class="en"></div><div class="ko"></div>`;
    div.querySelector(".py").textContent = zh ? (word.py || "") : "";
    div.querySelector(".en").textContent = mainText(word);
    div.querySelector(".ko").textContent = word.ko;
    words.appendChild(div);
  });

  const list = $("passage");
  list.innerHTML = "";
  topic.data.phrases.forEach((phrase, index) => {
    const li = document.createElement("li");
    li.dataset.index = String(index);
    li.innerHTML = `<div class="py"></div><div class="en"></div><div class="ko"></div>`;
    li.querySelector(".py").textContent = zh ? (phrase.py || "") : "";
    li.querySelector(".en").textContent = mainText(phrase);
    li.querySelector(".ko").textContent = phrase.ko;
    list.appendChild(li);
  });

  const prev = manifestTopics.find((item) => item.number === topic.meta.number - 1);
  const next = manifestTopics.find((item) => item.number === topic.meta.number + 1);
  $("prev").hidden = !prev;
  $("next").hidden = !next;
  if (prev) $("prev").href = topicHref(prev.number);
  if (next) $("next").href = topicHref(next.number);
}

function clearCurrent() {
  document.querySelectorAll(".current, .current-all").forEach((el) => {
    el.classList.remove("current", "current-all");
  });
}

function reveal(el, block) {
  if (!el) return;
  syncBarHeight();
  el.scrollIntoView({ behavior: "smooth", block });
}

function mark(selector, index) {
  clearCurrent();
  const el = document.querySelector(`${selector}[data-index="${index}"]`);
  if (el) {
    el.classList.add("current");
    reveal(el, "center");
  }
}

function waitWhilePaused() {
  if (!paused) return Promise.resolve();
  return new Promise((resolve) => pauseWaiters.push(resolve));
}

function setPlayback(rate) {
  audio.playbackRate = rate;
  audio.preservesPitch = true;
  audio.webkitPreservesPitch = true;
  audio.mozPreservesPitch = true;
}

function playUrl(url, id, rate) {
  return new Promise((resolve, reject) => {
    const finish = () => {
      audio.onended = null;
      audio.onerror = null;
      resolve(audio.duration || 0);
    };
    audio.onended = finish;
    audio.onerror = () => reject(new Error("음원을 재생할 수 없습니다."));
    audio.src = url;
    const applyRate = () => setPlayback(rate);
    audio.addEventListener("loadedmetadata", applyRate, { once: true });
    applyRate();
    audio.play().then(applyRate).catch(reject);
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

function repeatGap(duration, rate, extra, minimum, fallback) {
  const length = Number.isFinite(duration) ? duration : fallback;
  const played = length / (rate > 0 ? rate : 1);
  return Math.max(minimum, played + extra);
}

async function playRepeats(url, times, id, label, extra, minimum, fallback, rate) {
  for (let i = 1; i <= times; i += 1) {
    if (id !== runId) return;
    await waitWhilePaused();
    $("status").textContent = `${label} · ${i} / ${times}`;
    const duration = await playUrl(url, id, rate);
    if (id !== runId) return;
    await gap(repeatGap(duration, rate, extra, minimum, fallback), id);
  }
}

function clipBase(topic) {
  if (window.PREVIEW_CLIP_BASE) return window.PREVIEW_CLIP_BASE;
  if (currentLang === "zh") return `audio/zh/clips/${topic.id}`;
  return `audio/clips/${topic.id}`;
}

async function run(topic) {
  const id = ++runId;
  paused = false;
  setSettingsOpen(false);
  $("play").disabled = true;
  $("pause").disabled = false;
  const wordN = Number($("wordN").value);
  const sentN = Number($("sentN").value);
  const fullN = Number($("fullN").value);
  const wordRate = nearestRate($("wordRate").value);
  const sentRate = nearestRate($("sentRate").value);
  const base = clipBase(topic);
  const wordLabel = currentLang === "zh" ? "单词" : "단어";
  const sentLabel = currentLang === "zh" ? "句子" : "문장";
  const fullLabel = currentLang === "zh" ? "全文" : "본문 전체";
  try {
    if (wordN > 0) {
      for (let i = 0; i < topic.data.words.length; i += 1) {
        if (id !== runId) return;
        mark("#words .word", i);
        await playRepeats(`${base}/w${String(i + 1).padStart(2, "0")}.mp3`, wordN, id, `${wordLabel} ${i + 1}`, 0.6, 1.2, 0.6, wordRate);
      }
    }
    if (sentN > 0) {
      for (let i = 0; i < topic.data.phrases.length; i += 1) {
        if (id !== runId) return;
        mark("#passage li", i);
        await playRepeats(`${base}/s${String(i + 1).padStart(2, "0")}.mp3`, sentN, id, `${sentLabel} ${i + 1}`, 1.5, 0, 1, sentRate);
      }
    }
    if (fullN > 0) {
      clearCurrent();
      const passage = $("passage");
      passage.classList.add("current-all");
      reveal(passage.querySelector("li") || passage, "start");
      await playRepeats(`${base}/full.mp3`, fullN, id, fullLabel, 1.5, 0, 1, sentRate);
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
  const passage = $("passage");
  if (passage) passage.classList.remove("current-all");
}

async function main() {
  const settings = loadSettings();
  applySettings(settings);
  currentLang = initialLang();
  const topic = window.PREVIEW_TOPIC || await loadTopic();
  currentTopic = topic;
  setLang(currentLang, false);
  if (!new URLSearchParams(location.search).get("lang")) {
    const url = new URL(location.href);
    url.searchParams.set("lang", currentLang);
    history.replaceState(null, "", url);
  }

  ["wordN", "sentN", "fullN", "wordRate", "sentRate"].forEach((id) => {
    $(id).addEventListener("change", () => {
      saveSettings();
      updateSettingsSummary();
    });
  });
  $("settingsToggle").addEventListener("click", () => {
    setSettingsOpen($("controls").classList.contains("collapsed"));
  });
  window.addEventListener("resize", syncBarHeight);
  updateSettingsSummary();
  syncBarHeight();
  $("koToggle").addEventListener("click", () => {
    document.body.classList.toggle("hide-ko");
    $("koToggle").textContent = document.body.classList.contains("hide-ko")
      ? "한국어 뜻 보기"
      : "한국어 뜻 숨기기";
    saveSettings();
  });
  $("pyToggle").addEventListener("click", () => {
    document.body.classList.toggle("hide-py");
    $("pyToggle").textContent = document.body.classList.contains("hide-py")
      ? "拼音 보기"
      : "拼音 숨기기";
    saveSettings();
  });
  $("langEn").addEventListener("click", () => setLang("en", true));
  $("langZh").addEventListener("click", () => setLang("zh", true));
  $("play").addEventListener("click", () => {
    saveSettings();
    if (paused) {
      setSettingsOpen(false);
      paused = false;
      pauseWaiters.splice(0).forEach((fn) => fn());
      if (audio.src && audio.paused && !audio.ended) audio.play();
      $("play").disabled = true;
      $("pause").disabled = false;
      return;
    }
    run(currentTopic);
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

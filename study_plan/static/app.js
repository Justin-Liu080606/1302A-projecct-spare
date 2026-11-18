"use strict";

const $ = (id) => document.getElementById(id);
const palette = [
  ["#2195b0", "#dff3f8"], ["#986cd6", "#eee8fc"],
  ["#e49a43", "#fff1dc"], ["#39a882", "#def7ec"],
  ["#de7196", "#fdeaf0"], ["#4b7ccc", "#e6eefd"],
  ["#bf8351", "#f8eddf"], ["#7e9f4c", "#edf5df"]
];
const weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
let plan = null;
let weekStart = null;

function localDate(value) { return new Date(value + "T12:00:00"); }
function isoDate(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}
function addDays(value, n) {
  const copy = value instanceof Date ? new Date(value) : localDate(value);
  copy.setDate(copy.getDate() + n);
  return copy;
}
function mondayOf(value) {
  const d = value instanceof Date ? new Date(value) : localDate(value);
  d.setDate(d.getDate() - (d.getDay() + 6) % 7);
  return d;
}
function today() { return isoDate(new Date()); }
function minutesLabel(n) {
  const hour = Math.floor(n / 60), minutes = n % 60;
  return `${String(hour).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}
function hoursLabel(minutes) {
  return (minutes / 60).toLocaleString("en-US", {maximumFractionDigits:1}) + "h";
}
function subjectColor(id) { return palette[id % palette.length]; }
function clearChildren(node) { node.replaceChildren(); }
function addText(tag, className, content, parent) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  node.textContent = content;
  parent.appendChild(node);
  return node;
}

function addSubject(name = "", hours = "2", deadline = "") {
  const row = $("subject-template").content.firstElementChild.cloneNode(true);
  row.querySelector(".subject-name").value = name;
  row.querySelector(".subject-hours").value = hours;
  row.querySelector(".subject-deadline").value = deadline;
  row.querySelector(".remove-subject").addEventListener("click", () => {
    row.remove(); updateSubjectIndices();
  });
  row.querySelector(".move-subject-up").addEventListener("click", () => {
    if (row.previousElementSibling) {
      row.parentElement.insertBefore(row, row.previousElementSibling);
      updateSubjectIndices();
    }
  });
  row.querySelector(".move-subject-down").addEventListener("click", () => {
    if (row.nextElementSibling) {
      row.parentElement.insertBefore(row.nextElementSibling, row);
      updateSubjectIndices();
    }
  });
  $("subjects-list").appendChild(row);
  updateSubjectIndices();
}
function updateSubjectIndices() {
  $("subjects-list").querySelectorAll(".subject-row").forEach((row, i, all) => {
    row.querySelector(".subject-index").textContent = String(i + 1).padStart(2, "0");
    row.querySelector(".priority-badge").textContent = i === 0 ? "HIGHEST" : `P${i + 1}`;
    row.querySelector(".move-subject-up").disabled = i === 0;
    row.querySelector(".move-subject-down").disabled = i === all.length - 1;
  });
}
function addWindow(container, start = "08:00", end = "11:00") {
  const row = $("window-template").content.firstElementChild.cloneNode(true);
  row.querySelector(".window-start").value = start;
  row.querySelector(".window-end").value = end;
  row.querySelector(".remove-window").addEventListener("click", () => row.remove());
  container.appendChild(row);
}
function addOverride(day = $("start-date").value, windows = []) {
  const node = $("override-template").content.firstElementChild.cloneNode(true);
  const input = node.querySelector(".override-date");
  input.value = day;
  input.min = $("start-date").value;
  input.max = $("end-date").value;
  node.querySelector(".remove-override").addEventListener("click", () => node.remove());
  node.querySelector(".add-override-window").addEventListener("click", () => addWindow(node.querySelector(".override-windows")));
  windows.forEach(w => addWindow(node.querySelector(".override-windows"), w.start, w.end));
  $("overrides-list").appendChild(node);
}
function readWindows(container) {
  return Array.from(container.querySelectorAll(":scope > .window-row"), row => ({
    start: row.querySelector(".window-start").value,
    end: row.querySelector(".window-end").value
  }));
}
function requestBody() {
  return {
    start_date: $("start-date").value,
    end_date: $("end-date").value,
    subjects: Array.from($("subjects-list").children, row => ({
      name: row.querySelector(".subject-name").value.trim(),
      hours: row.querySelector(".subject-hours").value,
      exam_date: row.querySelector(".subject-deadline").value || null
    })),
    daily_windows: readWindows($("daily-windows")),
    date_overrides: Array.from($("overrides-list").children, row => ({
      date: row.querySelector(".override-date").value,
      windows: readWindows(row.querySelector(".override-windows"))
    })),
    session_minutes: Number($("session-minutes").value),
    break_minutes: Number($("break-minutes").value),
    daily_subject_limit_minutes: Number($("daily-subject-limit-minutes").value)
  };
}
function showError(message) {
  const el = $("error-message");
  el.textContent = message;
  el.hidden = false;
}
function resetError() { $("error-message").hidden = true; }

async function generate(event) {
  event.preventDefault();
  resetError();
  if (!$("subjects-list").children.length) {
    showError("Please add at least one subject.");
    return;
  }
  if (!$("planner-form").reportValidity()) return;
  const button = $("generate-button");
  button.disabled = true;
  button.querySelector("span").textContent = "Building your schedule…";
  try {
    const response = await fetch("/api/generate", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify(requestBody())
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Could not generate the schedule. Please check your inputs.");
    plan = result;
    weekStart = mondayOf(plan.start_date);
    renderPlan();
    $("plan-output").scrollIntoView({behavior: "smooth", block: "start"});
  } catch (err) {
    showError(err.message || "Cannot reach the local Python server. Please restart it and try again.");
  } finally {
    button.disabled = false;
    button.querySelector("span").textContent = "Generate study plan";
  }
}

function renderStats() {
  const summary = plan.summary;
  const info = [
    ["Required study time", hoursLabel(summary.required_minutes), "Across all subjects", ""],
    ["Available free time", hoursLabel(summary.available_minutes), "Before breaks", ""],
    ["Scheduled", hoursLabel(summary.scheduled_minutes), `${summary.session_count} study sessions`, "positive"],
    ["Unscheduled", hoursLabel(summary.remaining_minutes), summary.remaining_minutes ? "Consider adding more days" : "All hours allocated", summary.remaining_minutes ? "warning" : ""]
  ];
  const wrapper = $("stats-grid");
  clearChildren(wrapper);
  for (const [label, value, caption, status] of info) {
    const el = addText("div", "stat-card " + status, "", wrapper);
    addText("div", "stat-label", label, el);
    addText("div", "stat-value", value, el);
    addText("div", "stat-subtitle", caption, el);
  }
}
function renderWarnings() {
  const warnings = $("plan-warnings");
  clearChildren(warnings);
  const messages = plan.warnings || [];
  warnings.hidden = !messages.length;
  if (!messages.length) return;
  addText("div", "warnings-title", `⚠ Scheduling constraints · ${messages.length} subjects have remaining hours`, warnings);
  addText("div", "warnings-intro", `Daily per-subject cap: ${hoursLabel(plan.settings.daily_subject_limit_minutes)}. Some time may be unavailable due to breaks and deadlines.`, warnings);
  const list = addText("ul", "warnings-list", "", warnings);
  for (const message of messages) addText("li", "", message, list);
}
function renderProgress() {
  const list = $("subject-progress");
  clearChildren(list);
  const allDone = plan.summary.remaining_minutes === 0;
  const notice = $("notice-tag");
  notice.textContent = allDone ? "✓ Fully scheduled" : "! Hours remain";
  notice.classList.toggle("has-warning", !allDone);
  for (const subject of plan.subjects) {
    const [color] = subjectColor(subject.id);
    const item = addText("div", "progress-item", "", list);
    const head = addText("div", "progress-header", "", item);
    const label = addText("div", "progress-title", "", head);
    const marker = addText("span", "progress-marker", "", label);
    marker.style.setProperty("--color", color);
    addText("span", "", `P${subject.priority_rank ?? subject.id + 1} · ${subject.name}`, label);
    addText("span", "progress-meta", `${hoursLabel(subject.scheduled_minutes)} / ${hoursLabel(subject.required_minutes)}`, head);
    const track = addText("div", "progress-track", "", item);
    const fill = addText("div", "progress-fill", "", track);
    fill.style.setProperty("--color", color);
    fill.style.width = `${subject.scheduled_minutes / subject.required_minutes * 100}%`;
    const hints = [];
    if (subject.exam_date) hints.push(`Exam date ${subject.exam_date}`);
    if (subject.remaining_minutes) {
      hints.push(`Unscheduled ${hoursLabel(subject.remaining_minutes)}`);
      if (subject.required_minutes > subject.individual_capacity_upper_bound_minutes) {
        hints.push(`Theoretical individual capacity ${hoursLabel(subject.individual_capacity_upper_bound_minutes)}`);
      }
    }
    else hints.push("All required hours scheduled");
    addText("div", "progress-hint", hints.join(" · "), item);
  }
}
function renderCalendar() {
  if (!plan) return;
  const startWeek = isoDate(weekStart);
  const finishWeek = isoDate(addDays(weekStart, 6));
  $("previous-week").disabled = startWeek <= isoDate(mondayOf(plan.start_date));
  $("next-week").disabled = finishWeek >= plan.end_date;
  const dateFormat = (d) => d.toLocaleDateString("en-US", {month: "short", day: "numeric"});
  $("week-title").textContent = `${dateFormat(weekStart)} – ${dateFormat(addDays(weekStart, 6))}`;

  const allDates = Array.from({length:7}, (_, idx) => isoDate(addDays(weekStart, idx)));
  const weekSessions = plan.sessions.filter(s => s.date >= startWeek && s.date <= finishWeek);
  const weekWindows = plan.availability.filter(s => s.date >= startWeek && s.date <= finishWeek);
  const anchors = weekSessions.flatMap(s => [s.start, s.end]).concat(weekWindows.flatMap(w => [w.start, w.end]));
  const startHour = anchors.length ? Math.floor(Math.min(...anchors) / 60) : 8;
  const endHour = anchors.length ? Math.ceil(Math.max(...anchors) / 60) : 18;
  const length = Math.max(4, endHour - startHour);
  const hourHeight = 64;
  const bodyHeight = length * hourHeight;
  const pxPerMinute = hourHeight / 60;
  const calendar = $("calendar");
  clearChildren(calendar);
  const head = addText("div", "calendar-head", "", calendar);
  addText("div", "", "", head);
  const todayDate = today();
  for (const date of allDates) {
    const d = localDate(date);
    const outside = date < plan.start_date || date > plan.end_date;
    const dayEl = addText("div", "day-head" + (outside ? " is-outside" : "") + (date === todayDate ? " is-today" : ""), "", head);
    addText("div", "day-name", weekdays[d.getDay()], dayEl);
    addText("div", "day-date", String(d.getDate()), dayEl);
  }
  const body = addText("div", "time-body", "", calendar);
  const axis = addText("div", "time-axis", "", body);
  axis.style.height = bodyHeight + "px";
  for (let h = startHour; h <= startHour + length; h++) {
    const label = addText("div", "time-label", minutesLabel(h * 60), axis);
    label.style.top = (h - startHour) * hourHeight + "px";
  }
  for (const date of allDates) {
    const outside = date < plan.start_date || date > plan.end_date;
    const col = addText("div", "calendar-day" + (outside ? " outside" : ""), "", body);
    col.style.height = bodyHeight + "px";
    for (const w of weekWindows.filter(s => s.date === date)) {
      const free = addText("div", "available-block", "", col);
      free.style.top = ((w.start - startHour * 60) * pxPerMinute) + "px";
      free.style.height = ((w.end - w.start) * pxPerMinute) + "px";
    }
    for (const s of weekSessions.filter(s => s.date === date)) {
      const event = addText("div", "calendar-event" + (s.end - s.start < 50 ? " short" : ""), "", col);
      const [color, bg] = subjectColor(s.subject_id);
      event.style.setProperty("--color", color);
      event.style.setProperty("--bg", bg);
      event.style.top = ((s.start - startHour * 60) * pxPerMinute + 2) + "px";
      event.style.height = Math.max(26, (s.end - s.start) * pxPerMinute - 4) + "px";
      event.title = `${s.subject} · ${s.start_time}–${s.end_time}`;
      addText("strong", "", s.subject, event);
      addText("small", "", `${s.start_time}–${s.end_time}`, event);
    }
  }
}
function renderPlan() {
  $("empty-state").hidden = true;
  $("plan-output").hidden = false;
  renderStats();
  renderWarnings();
  renderProgress();
  renderCalendar();
}
function populateDemo() {
  clearChildren($("subjects-list"));
  addSubject("CS1302 Python", "10");
  addSubject("Mathematics", "8");
  addSubject("English", "6");
  const start = addDays(today(), 1);
  $("start-date").value = isoDate(start);
  $("end-date").value = isoDate(addDays(start, 6));
  clearChildren($("daily-windows"));
  addWindow($("daily-windows"), "08:00", "11:00");
  addWindow($("daily-windows"), "14:00", "17:00");
  clearChildren($("overrides-list"));
  $("session-minutes").value = "60";
  $("break-minutes").value = "10";
  $("daily-subject-limit-minutes").value = "120";
  resetError();
}
function init() {
  populateDemo();
  $("planner-form").addEventListener("submit", generate);
  $("load-demo").addEventListener("click", populateDemo);
  $("add-subject").addEventListener("click", () => addSubject());
  $("add-window").addEventListener("click", () => addWindow($("daily-windows"), "18:00", "20:00"));
  $("add-override").addEventListener("click", () => {
    const known = new Set(Array.from($("overrides-list").children, e => e.querySelector(".override-date").value));
    let candidate = $("start-date").value;
    while (candidate <= $("end-date").value && known.has(candidate)) candidate = isoDate(addDays(candidate, 1));
    addOverride(candidate <= $("end-date").value ? candidate : $("start-date").value);
    $("overrides-details").open = true;
  });
  $("previous-week").addEventListener("click", () => {
    weekStart = addDays(weekStart, -7); renderCalendar();
  });
  $("next-week").addEventListener("click", () => {
    weekStart = addDays(weekStart, 7); renderCalendar();
  });
  $("today-week").addEventListener("click", () => {
    weekStart = mondayOf(plan.start_date); renderCalendar();
  });
}
document.addEventListener("DOMContentLoaded", init);

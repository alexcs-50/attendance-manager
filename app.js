"use strict";
const el = id => document.getElementById(id);
let students = [], original = {}, marks = {}, loadedDay = "";
function notice(message) { el("notice").textContent = message; }
async function api(url, body) {
  const options = body ? {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)} : {};
  const response = await fetch(url, options);
  const result = await response.json();
  if (!response.ok) throw new Error(result.error);
  return result;
}
function table(target, headers, rows, emptyText) {
  const box = el(target);
  box.replaceChildren();
  if (!rows.length) { box.textContent = emptyText; return; }
  const t = document.createElement("table"), head = t.createTHead().insertRow();
  for (const label of headers) {
    const th = document.createElement("th");
    th.scope = "col"; th.textContent = label; head.append(th);
  }
  const body = t.createTBody();
  for (const values of rows) {
    const tr = body.insertRow();
    for (const value of values) tr.insertCell().append(value);
  }
  box.append(t);
}
function counts() {
  const statuses = Object.values(marks);
  el("counts").replaceChildren();
  for (const [label, value] of [["Present","Present"],["Absent","Absent"],["Unmarked",null]]) {
    const card = document.createElement("div"), total = document.createElement("strong");
    total.textContent = statuses.filter(s => s === value).length;
    card.append(total, label); el("counts").append(card);
  }
}
function choices(student) {
  const group = document.createElement("div");
  for (const status of ["Present","Absent"]) {
    const label = document.createElement("label"), input = document.createElement("input");
    label.className = "choice"; input.type = "radio"; input.name = "student-" + student.id;
    input.setAttribute("aria-label", student.roll + " " + status);
    input.checked = marks[student.id] === status;
    input.onchange = () => { marks[student.id] = status; counts(); notice("Unsaved attendance changes."); };
    label.append(input, status); group.append(label);
  }
  return group;
}
function render() {
  table("sheet", ["Roll","Student","Status"], students.map(s => [s.roll,s.name,choices(s)]), "Open Students to add your first student.");
  table("students", ["Roll","Student"], students.map(s => [s.roll,s.name]), "Your class roster is empty.");
  el("all").disabled = el("save").disabled = !students.length;
  counts();
}
async function load(day) {
  const requestDay = day || "";
  const result = await api("/api/register" + (day ? "?day=" + encodeURIComponent(day) : ""));
  if (requestDay && el("day").value !== requestDay) return;
  loadedDay = result.day; el("day").value = loadedDay; students = result.students;
  original = Object.fromEntries(students.map(s => [s.id,s.status]));
  marks = {...original}; render();
}
function dirty() { return Object.keys(marks).some(id => marks[id] !== original[id]); }
function discard() { return !dirty() || confirm("Discard unsaved attendance changes?"); }
function run(action) {
  return async event => {
    event.preventDefault();
    try { await action(); } catch (error) { notice(error.message); }
  };
}
for (const b of document.querySelectorAll("nav button")) b.onclick = () => {
  for (const section of document.querySelectorAll("section")) section.hidden = section.id !== b.dataset.page;
  for (const button of document.querySelectorAll("nav button")) button.setAttribute("aria-pressed", String(button === b));
  notice("");
};
async function reloadDay() {
  if (!discard()) { el("day").value = loadedDay; return; }
  if (!el("day").value) { el("day").value = loadedDay; return; }
  try { await load(el("day").value); notice(""); }
  catch (err) { el("day").value = loadedDay; throw err; }
}
el("day").onchange = el("reload").onclick = run(reloadDay);
el("all").onclick = () => { for (const s of students) marks[s.id] = "Present"; render(); notice("Review the marks, then save the register."); };
function clearReport() {
  el("csv").hidden = true; el("results").replaceChildren();
  el("caption").textContent = "Select View summary for the current date range.";
}
el("save").onclick = run(async () => {
  if (loadedDay !== el("day").value) throw new Error("Reload the selected day before saving.");
  if (Object.values(marks).includes(null)) throw new Error("Select a status for every student.");
  await api("/api/register", {day:loadedDay, original, marks});
  await load(loadedDay); clearReport(); notice("Attendance saved for " + loadedDay + ".");
});
el("add").onsubmit = run(async () => {
  if (!discard()) return;
  await api("/api/students", {roll:el("roll").value, name:el("name").value});
  await load(loadedDay); el("add").reset(); clearReport(); notice("Student added to the roster.");
});
el("range").oninput = clearReport;
el("range").onsubmit = run(async () => {
  clearReport();
  const query = new URLSearchParams({start:el("start").value, end:el("end").value});
  const rows = await api("/api/report?" + query);
  table("results", ["Roll","Student","Marked","Present","Absent","Attendance"], rows.map(r =>
    [r.roll,r.name,String(r.marked),String(r.present),String(r.absent),r.percent === null ? "—" : r.percent.toFixed(1) + "%"]), "No students in the roster.");
  el("csv").href = "/summary.csv?" + query; el("csv").hidden = false;
  el("caption").textContent = query.get("start") + " to " + query.get("end") + " · Percentage uses days marked for each student.";
});
load().then(() => {
  for (const id of ["day","start","end"]) el(id).max = loadedDay;
  el("start").value = loadedDay.slice(0,8) + "01"; el("end").value = loadedDay;
}).catch(err => notice(err.message));

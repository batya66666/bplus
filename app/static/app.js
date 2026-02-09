// app/static/app.js

const API = ""; // same origin
const tokenKey = "lms_token";

const $ = (id) => document.getElementById(id);

function toast(msg) {
  const t = $("toast");
  if (!t) return;
  t.textContent = msg;
  t.classList.remove("hidden");
  setTimeout(() => t.classList.add("hidden"), 2600);
}

function setToken(token) { localStorage.setItem(tokenKey, token); }
function getToken() { return localStorage.getItem(tokenKey); }
function clearToken() { localStorage.removeItem(tokenKey); }

function escapeHtml(s) {
  return (s ?? "")
    .toString()
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

async function apiFetch(path, opts = {}) {
  const headers = new Headers(opts.headers || {});
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  if (opts.jsonBody !== undefined) {
    headers.set("Content-Type", "application/json");
    opts.body = JSON.stringify(opts.jsonBody);
  }

  const res = await fetch(API + path, {
    method: opts.method || "GET",
    headers,
    body: opts.body,
  });

  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }

  if (!res.ok) {
    let err = `HTTP ${res.status}`;
    if (data && data.detail !== undefined) {
      err = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    } else if (typeof data === "string" && data.trim()) {
      err = data;
    }
    throw new Error(err);
  }
  return data;
}

function showLogin(isLogin) {
  $("loginView")?.classList.toggle("hidden", !isLogin);
  $("appView")?.classList.toggle("hidden", isLogin);
  $("logoutBtn")?.classList.toggle("hidden", isLogin);
}

function renderList(el, items, renderItem) {
  if (!el) return;
  el.innerHTML = "";
  if (!items || items.length === 0) {
    el.innerHTML = `<div class="item"><div class="muted">Пусто</div></div>`;
    return;
  }
  for (const it of items) el.appendChild(renderItem(it));
}

function selectTab(name) {
  document.querySelectorAll(".tab").forEach(b =>
    b.classList.toggle("active", b.dataset.tab === name)
  );

  ["courses", "standups", "documents", "profile", "admin"].forEach(t => {
    $("tab-" + t)?.classList.toggle("hidden", t !== name);
  });
}

// ---------- ME ----------
let meCache = null;

async function loadMe() {
  const me = await apiFetch("/users/me");
  meCache = me;

  const adminBtn = $("adminTabBtn");
  if (adminBtn) {
    if (me.role === "ADMIN") adminBtn.classList.remove("hidden");
    else adminBtn.classList.add("hidden");
  }

  const badge = $("meBadge");
  if (badge) {
    badge.textContent = `${me.full_name} • ${me.role}`;
    badge.classList.remove("hidden");
  }

  $("profileJson") && ($("profileJson").textContent = JSON.stringify(me, null, 2));
  return me;
}

// ---------- COURSES helpers ----------
function fmtDate(iso) {
  if (!iso) return "-";
  try { return new Date(iso).toLocaleDateString(); } catch { return iso; }
}

function statusRu(s) {
  if (s === "ASSIGNED") return "Назначен";
  if (s === "IN_PROGRESS") return "В процессе";
  if (s === "COMPLETED") return "Завершён";
  return s || "-";
}

function isOverdue(deadlineIso, status) {
  if (!deadlineIso) return false;
  if (status === "COMPLETED") return false;
  const d = new Date(deadlineIso);
  if (Number.isNaN(d.getTime())) return false;
  return d.getTime() < Date.now();
}

// ---------- COURSES: start + API ----------
async function loadCatalogCourses() {
  return await apiFetch("/courses/catalog");
}

async function startCourse(courseId) {
  await apiFetch(`/courses/${courseId}/start`, { method: "POST" });
}

// ---------- COURSES: My courses (filters) ----------
let myCoursesCache = [];
let myFilter = "ALL"; // ALL | ACTIVE | COMPLETED

function filterMyCourses(list) {
  if (myFilter === "ALL") return list;
  if (myFilter === "COMPLETED") return list.filter(c => c.status === "COMPLETED");
  // ACTIVE = ASSIGNED + IN_PROGRESS
  return list.filter(c => c.status === "ASSIGNED" || c.status === "IN_PROGRESS");
}

function setMyFilter(name) {
  myFilter = name;

  const map = {
    ALL: $("myFilterAll"),
    ACTIVE: $("myFilterActive"),
    COMPLETED: $("myFilterCompleted"),
  };

  Object.entries(map).forEach(([k, btn]) => {
    if (!btn) return;
    btn.classList.toggle("activeFilter", k === myFilter);
  });

  renderMyCourses();
}

function renderMyCourses() {
  const list = filterMyCourses(myCoursesCache);

  renderList($("myCoursesList"), list, (c) => {
    const d = document.createElement("div");
    
    // Determine accent class
    let accentClass = "item";
    const overdue = isOverdue(c.deadline_at, c.status);
    
    if (overdue) {
      accentClass += " accent-red";
    } else if (c.status === "COMPLETED") {
      accentClass += " accent-green";
    } else if (c.status === "IN_PROGRESS") {
      accentClass += " accent-blue";
    } else if (c.status === "ASSIGNED") {
      accentClass += " accent-yellow";
    }
    
    d.className = accentClass;

    const lessons = c.lessons || [];
    const lessonsHtml = lessons.length
      ? lessons.map(l => {
          const done = l.is_completed ? "✅" : "";
          return `<div class="muted">${l.order}. ${escapeHtml(l.title)} ${done}</div>`;
        }).join("")
      : `<div class="muted">Уроки пока не добавлены</div>`;

    let btnHtml = "";
    if (c.status === "ASSIGNED") btnHtml = `<button class="btn startBtn">Начать обучение</button>`;
    else btnHtml = `<button class="btn secondary openBtn">Открыть курс</button>`;

    d.innerHTML = `
      <div class="title">${escapeHtml(c.title)} <span class="badge">${statusRu(c.status)}</span></div>
      <div class="muted">${escapeHtml(c.description || "")}</div>
      <div class="muted">Прогресс: ${c.progress_percent ?? 0}% • Дедлайн: ${fmtDate(c.deadline_at)}</div>
      <div class="mt">${lessonsHtml}</div>
      <div class="row" style="margin-top:10px; gap:10px;">
        ${btnHtml}
      </div>
    `;

    const startBtn = d.querySelector(".startBtn");
    if (startBtn) startBtn.addEventListener("click", async () => {
      try {
        await startCourse(c.id);
        toast("Обучение начато");
        await loadMyCourses(); // обновим статус
        openPlayerStub({ ...c, status: "IN_PROGRESS" }); // откроем плеер-заглушку
      } catch (e) {
        toast(e.message);
      }
    });

    const openBtn = d.querySelector(".openBtn");
    if (openBtn) openBtn.addEventListener("click", () => openPlayerStub(c));

    return d;
  });
}

async function loadMyCourses() {
  const list = await apiFetch("/courses/my_full");
  myCoursesCache = list || [];
  renderMyCourses();
}

// ---------- COURSES: Catalog (Library) ----------
let libraryCoursesCache = [];

function dedupById(list) {
  const seen = new Set();
  const uniq = [];
  for (const c of (list || [])) {
    if (seen.has(c.id)) continue;
    seen.add(c.id);
    uniq.push(c);
  }
  return uniq;
}

async function loadCatalog() {
  const cat = await loadCatalogCourses();
  libraryCoursesCache = dedupById(cat);
  renderCatalogGrid();
}

function renderCatalogGrid() {
  const grid = $("catalogCoursesGrid");
  if (!grid) return;

  grid.innerHTML = "";
  const list = libraryCoursesCache || [];

  if (!list.length) {
    grid.innerHTML = `<div class="item"><div class="muted">Пусто</div></div>`;
    return;
  }

  for (const c of list) {
    const card = document.createElement("div");
    const overdue = isOverdue(c.deadline_at, c.status);
    card.className = "course-card" + (overdue ? " overdue" : "");

    const progress = Math.max(0, Math.min(100, c.progress_percent ?? 0));
    const deadlineText = c.deadline_at ? fmtDate(c.deadline_at) : "-";
    const coverText = (c.title || "Курс").slice(0, 32);

    card.innerHTML = `
      <div class="course-cover"><div class="coverText">${escapeHtml(coverText)}</div></div>
      <div class="course-title">${escapeHtml(c.title)}</div>
      <div class="progress"><div style="width:${progress}%"></div></div>
      <div class="course-meta">
        <div>${statusRu(c.status)}</div>
        <div>Дедлайн: ${deadlineText}</div>
      </div>
    `;

    // DoD: клик по карточке -> заглушка плеера
    card.addEventListener("click", () => openPlayerStub(c));
    grid.appendChild(card);
  }
}

function openCatalog() {
  $("catalogView")?.classList.remove("hidden");
  $("playerView")?.classList.add("hidden");
  loadCatalog().catch(e => toast(e.message));
}

function closeCatalog() {
  $("catalogView")?.classList.add("hidden");
}

// ---------- Player stub ----------
function openPlayerStub(course) {
  // Показываем плеер, прячем каталог (если открыт)
  $("catalogView")?.classList.add("hidden");
  $("playerView")?.classList.remove("hidden");

  $("playerTitle") && ($("playerTitle").textContent = course.title || "Плеер");
  $("playerCourseId") && ($("playerCourseId").textContent = String(course.id));
}

function backToLibrary() {
  // Возвратим к каталогу только если он был открыт кнопкой
  // (если нет — просто скроем плеер)
  $("playerView")?.classList.add("hidden");
  $("catalogView")?.classList.remove("hidden");
}

// ---------- STANDUPS ----------
let editingReportId = null;

function reportStatusRu(s) {
  if (s === "PENDING") return "На проверке";
  if (s === "REVISION") return "На доработке";
  if (s === "ACCEPTED") return "Принят";
  return s || "-";
}

function setSendButtonMode() {
  const btn = $("sendStandup");
  if (!btn) return;
  btn.textContent = editingReportId ? "Сдать доработку" : "Отправить отчёт";
}

async function loadMyReports() {
  const list = await apiFetch("/standups/my");

  renderList($("reportsList"), list, (r) => {
    const d = document.createElement("div");
    d.className = "item";

    d.innerHTML = `
      <div class="title">День ${r.day_number} • ${reportStatusRu(r.status)}</div>
      <div class="muted">Сделал: ${escapeHtml(r.text_done)}</div>
      <div class="muted">План: ${escapeHtml(r.text_plan)}</div>
      <div class="muted">Блокеры: ${escapeHtml(r.text_blockers)}</div>
      ${r.mentor_comment ? `<div class="muted">Комментарий: ${escapeHtml(r.mentor_comment)}</div>` : ""}

      <div class="row" style="margin-top:10px; gap:10px;">
        ${r.status === "REVISION" ? `<button class="btn secondary reviseBtn">Доработать</button>` : ""}
        <button class="btn secondary histBtn">История</button>
      </div>
      <div class="history hidden" style="margin-top:10px;"></div>
    `;

    const reviseBtn = d.querySelector(".reviseBtn");
    const histBtn = d.querySelector(".histBtn");
    const histBox = d.querySelector(".history");

    if (reviseBtn) {
      reviseBtn.addEventListener("click", () => {
        editingReportId = r.id;
        $("dayNumber").value = r.day_number;
        $("doneText").value = r.text_done;
        $("planText").value = r.text_plan;
        $("blockersText").value = r.text_blockers;
        setSendButtonMode();
        toast("Исправь текст и нажми «Сдать доработку»");
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
    }

    histBtn.addEventListener("click", async () => {
      try {
        if (!histBox.classList.contains("hidden")) {
          histBox.classList.add("hidden");
          histBox.innerHTML = "";
          return;
        }

        const hist = await apiFetch(`/standups/${r.id}/history`);
        histBox.classList.remove("hidden");

        histBox.innerHTML = (hist || []).map(h => `
          <div class="item">
            <div class="muted">${new Date(h.created_at).toLocaleString()} • <b>${reportStatusRu(h.status)}</b></div>
            ${h.mentor_comment ? `<div class="muted">Комментарий: ${escapeHtml(h.mentor_comment)}</div>` : ""}
            <div class="muted">Сделал: ${escapeHtml(h.text_done)}</div>
            <div class="muted">План: ${escapeHtml(h.text_plan)}</div>
            <div class="muted">Блокеры: ${escapeHtml(h.text_blockers)}</div>
          </div>
        `).join("");
      } catch (e) {
        toast(e.message);
      }
    });

    return d;
  });
}

async function submitStandup() {
  const day_number = Number($("dayNumber").value || 1);
  const text_done = $("doneText").value;
  const text_plan = $("planText").value;
  const text_blockers = $("blockersText").value;

  if (editingReportId) {
    await apiFetch(`/standups/${editingReportId}`, {
      method: "PUT",
      jsonBody: { text_done, text_plan, text_blockers },
    });
    toast("Доработка отправлена на проверку");
    editingReportId = null;
    setSendButtonMode();
  } else {
    await apiFetch("/standups", {
      method: "POST",
      jsonBody: { day_number, text_done, text_plan, text_blockers },
    });
    toast("Отчёт отправлен");
  }

  await loadMyReports();
}

// ---------- STANDUPS (MENTOR) ----------
async function loadMentorReports() {
  const title = $("mentorBlockTitle");
  const box = $("mentorReports");
  if (!title || !box) return;

  const me = meCache || (await loadMe());
  const allowed = (me.role === "MENTOR" || me.role === "TEAM_LEAD" || me.role === "ADMIN");
  if (!allowed) {
    title.style.display = "none";
    box.style.display = "none";
    box.innerHTML = "";
    return;
  }

  const list = await apiFetch("/standups/mentor");
  title.style.display = "block";
  box.style.display = "block";

  renderList(box, list, (r) => {
    const el = document.createElement("div");
    el.className = "item";

    el.innerHTML = `
      <div class="title">${escapeHtml(r.user_full_name)} <span class="badge">${escapeHtml(r.user_email)}</span></div>
      <div class="muted">День ${r.day_number} • <b>${reportStatusRu(r.status)}</b></div>
      <div class="muted">Сделал: ${escapeHtml(r.text_done)}</div>
      <div class="muted">План: ${escapeHtml(r.text_plan)}</div>
      <div class="muted">Блокеры: ${escapeHtml(r.text_blockers)}</div>

      <div class="row" style="margin-top:10px; gap:10px; align-items:flex-start;">
        <input class="mentorComment" placeholder="Комментарий ментора..." value="${escapeHtml(r.mentor_comment || "")}" style="flex:1;" />
        <button class="btn secondary acceptBtn">Принять</button>
        <button class="btn secondary revisionBtn">На доработку</button>
      </div>
    `;

    const commentInp = el.querySelector(".mentorComment");
    const acceptBtn = el.querySelector(".acceptBtn");
    const revisionBtn = el.querySelector(".revisionBtn");

    acceptBtn.addEventListener("click", async () => {
      try {
        await apiFetch(`/standups/${r.id}/mentor_decision`, {
          method: "POST",
          jsonBody: { action: "ACCEPTED", mentor_comment: commentInp.value || "" },
        });
        toast("Отчёт принят");
        await loadMentorReports();
        await loadMyReports();
      } catch (e) { toast(e.message); }
    });

    revisionBtn.addEventListener("click", async () => {
      try {
        const c = (commentInp.value || "").trim();
        if (!c) { toast("Комментарий обязателен"); return; }
        await apiFetch(`/standups/${r.id}/mentor_decision`, {
          method: "POST",
          jsonBody: { action: "REVISION", mentor_comment: c },
        });
        toast("Отправлено на доработку");
        await loadMentorReports();
      } catch (e) { toast(e.message); }
    });

    return el;
  });
}

// ---------- DOCUMENTS ----------
async function loadDocs(q = "") {
  const qs = q ? `?q=${encodeURIComponent(q)}` : "";
  const list = await apiFetch("/documents" + qs);

  renderList($("docsList"), list, (doc) => {
    const d = document.createElement("div");
    d.className = "item";
    d.innerHTML = `
      <div class="title">${escapeHtml(doc.title)}</div>
      <div class="muted">Категория: ${escapeHtml(doc.category)} • Доступ: ${escapeHtml(doc.access_level)}</div>
      <div class="muted"><a href="${doc.file_url}" target="_blank">Открыть</a></div>
    `;
    return d;
  });
}

// ---------- ADMIN ----------
async function loadDepartments() {
  const deps = await apiFetch("/departments");

  const sel = $("newUserDept");
  if (sel) {
    sel.innerHTML = `<option value="">— не выбран —</option>`;
    for (const d of deps) {
      const opt = document.createElement("option");
      opt.value = String(d.id);
      opt.textContent = d.name;
      sel.appendChild(opt);
    }
  }

  const listEl = $("deptsList");
  if (listEl) {
    renderList(listEl, deps, (d) => {
      const el = document.createElement("div");
      el.className = "item";
      el.innerHTML = `<div class="title">${escapeHtml(d.name)}</div><div class="muted">id: ${d.id}</div>`;
      return el;
    });
  }

  return deps;
}

async function createDepartmentFromForm() {
  const name = ($("newDeptName")?.value || "").trim();
  if (!name) { toast("Название отдела пустое"); return; }
  await apiFetch("/departments", { method: "POST", jsonBody: { name } });
  $("newDeptName").value = "";
  toast("Отдел добавлен");
  await loadDepartments();
}

async function loadUsers() {
  const list = await apiFetch("/users");
  renderList($("usersList"), list, (u) => {
    const d = document.createElement("div");
    d.className = "item";
    d.innerHTML = `
      <div class="title">${escapeHtml(u.full_name)} <span class="badge">${escapeHtml(u.role)}</span></div>
      <div class="muted">${escapeHtml(u.email)} • dept_id: ${u.department_id ?? "-"}</div>
    `;
    return d;
  });

  return list;
}

async function createUserFromForm() {
  const email = ($("newUserEmail")?.value || "").trim();
  const full_name = ($("newUserName")?.value || "").trim();
  const password = $("newUserPass")?.value || "";
  const role = $("newUserRole")?.value || "EMPLOYEE";
  const depVal = $("newUserDept")?.value || "";
  const department_id = depVal ? Number(depVal) : null;

  if (!email || !full_name || !password) { toast("Заполни email/ФИО/пароль"); return; }

  await apiFetch("/users", { method: "POST", jsonBody: { email, full_name, role, department_id, password } });
  toast("Пользователь создан");
  $("newUserPass").value = "";
  await loadUsers();
}

async function loadAssignDropdowns() {
  const users = await apiFetch("/users");
  const courses = await apiFetch("/courses");

  const uSel = $("assignUser");
  const cSel = $("assignCourse");

  if (uSel) {
    uSel.innerHTML = "";
    for (const u of users) {
      const opt = document.createElement("option");
      opt.value = String(u.id);
      opt.textContent = `${u.full_name} (${u.email})`;
      uSel.appendChild(opt);
    }
  }

  if (cSel) {
    cSel.innerHTML = "";
    for (const c of courses) {
      const opt = document.createElement("option");
      opt.value = String(c.id);
      opt.textContent = c.title;
      cSel.appendChild(opt);
    }
  }
}

async function assignCourseFromForm() {
  const user_id = Number($("assignUser")?.value || 0);
  const course_id = Number($("assignCourse")?.value || 0);
  if (!user_id || !course_id) { toast("Выбери пользователя и курс"); return; }

  await apiFetch("/courses/assign", { method: "POST", jsonBody: { user_id, course_id } });
  toast("Курс назначен");
}

// ---------- UI events ----------
$("loginBtn")?.addEventListener("click", async () => {
  try {
    const email = ($("email")?.value || "").trim();
    const password = $("password")?.value || "";
    const data = await apiFetch("/auth/login", { method: "POST", jsonBody: { email, password } });

    setToken(data.access_token);
    toast("Вход выполнен");
    showLogin(false);

    await loadMe();
    selectTab("courses");
    setMyFilter("ALL");
    await loadMyCourses();
  } catch (e) {
    toast(e.message || "Ошибка входа");
  }
});

$("logoutBtn")?.addEventListener("click", () => {
  clearToken();
  meCache = null;
  $("meBadge")?.classList.add("hidden");
  toast("Вы вышли");
  showLogin(true);
});

// My courses filters
$("myFilterAll")?.addEventListener("click", () => setMyFilter("ALL"));
$("myFilterActive")?.addEventListener("click", () => setMyFilter("ACTIVE"));
$("myFilterCompleted")?.addEventListener("click", () => setMyFilter("COMPLETED"));

// Catalog open/close
$("openCatalogBtn")?.addEventListener("click", () => openCatalog());
$("openCatalogBtn2")?.addEventListener("click", () => openCatalog());
$("closeCatalogBtn")?.addEventListener("click", () => closeCatalog());

// Player back
$("backToLibrary")?.addEventListener("click", () => backToLibrary());

document.querySelectorAll(".tab").forEach(b => {
  b.addEventListener("click", async () => {
    const name = b.dataset.tab;
    selectTab(name);

    try {
      if (name === "courses") {
        setMyFilter(myFilter); // просто перерендер
        await loadMyCourses();
      }

      if (name === "standups") {
        await loadMyReports();
        await loadMentorReports();
      }

      if (name === "documents") await loadDocs(($("docQuery")?.value || "").trim());
      if (name === "profile") await loadMe();

      if (name === "admin") {
        await loadDepartments();
        await loadUsers();
        await loadAssignDropdowns();
      }
    } catch (e) {
      toast(e.message);
    }
  });
});

$("refreshCourses")?.addEventListener("click", () => loadMyCourses().catch(e => toast(e.message)));
$("refreshReports")?.addEventListener("click", () => loadMyReports().catch(e => toast(e.message)));
$("sendStandup")?.addEventListener("click", () => submitStandup().catch(e => toast(e.message)));

$("searchDocs")?.addEventListener("click", () => loadDocs(($("docQuery")?.value || "").trim()).catch(e => toast(e.message)));

$("createDeptBtn")?.addEventListener("click", () => createDepartmentFromForm().catch(e => toast(e.message)));
$("refreshDeptsBtn")?.addEventListener("click", () => loadDepartments().catch(e => toast(e.message)));

$("createUserBtn")?.addEventListener("click", () => createUserFromForm().catch(e => toast(e.message)));
$("refreshUsersBtn")?.addEventListener("click", () => loadUsers().catch(e => toast(e.message)));

$("assignBtn")?.addEventListener("click", () => assignCourseFromForm().catch(e => toast(e.message)));

// ---------- Boot ----------
(async function boot() {
  setSendButtonMode();

  const token = getToken();
  if (!token) { showLogin(true); return; }

  try {
    showLogin(false);
    await loadMe();
    selectTab("courses");
    setMyFilter("ALL");
    await loadMyCourses();
  } catch (e) {
    clearToken();
    showLogin(true);
  }
})();
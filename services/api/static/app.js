const teamsEl = document.getElementById("teams");
const teamStyleEl = document.getElementById("team-style");
const matchesEl = document.getElementById("matches");
const detailEl = document.getElementById("detail");
const teamsCountEl = document.getElementById("teams-count");
const activeTeamEl = document.getElementById("active-team");
const activeMatchEl = document.getElementById("active-match");

let activeTeamSlug = null;
let activeMatchId = null;

async function fetchJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Failed to load ${path}: ${response.status}`);
  }
  return response.json();
}

function renderTags(items = [], className = "") {
  if (!items.length) {
    return "";
  }

  return `
    <div class="tag-row">
      ${items.map((item) => `<span class="tag ${className}">${item}</span>`).join("")}
    </div>
  `;
}

function renderStatus(status) {
  return `<span class="tag status-${status}">${status.replace("_", " ")}</span>`;
}

function renderMetrics(metrics = []) {
  if (!metrics.length) {
    return `<p class="detail-copy">No computed team metrics yet.</p>`;
  }

  return `
    <section class="metric-grid">
      ${metrics
        .map(
          (metric) => `
            <article class="metric-card">
              <span class="metric-label">${metric.label}</span>
              <strong class="metric-value">${metric.display_value}</strong>
            </article>
          `
        )
        .join("")}
    </section>
  `;
}

function renderCompactMetrics(metrics = []) {
  if (!metrics.length) {
    return "";
  }

  return `
    <section class="metric-grid">
      ${metrics
        .map(
          (metric) => `
            <article class="metric-card compact">
              <span class="metric-label">${metric.label}</span>
              <strong class="metric-value">${metric.display_value}</strong>
            </article>
          `
        )
        .join("")}
    </section>
  `;
}

function teamCard(team) {
  return `
    <button class="card ${team.team_slug === activeTeamSlug ? "active" : ""}" data-team-slug="${team.team_slug}">
      <h3 class="card-title">${team.name}</h3>
      <div class="card-meta">${team.team_type} ${team.editorial_focus ? "| editorial focus" : ""}</div>
      ${renderTags([team.team_slug], "")}
    </button>
  `;
}

function matchCard(match) {
  return `
    <button class="card ${match.match_id === activeMatchId ? "active" : ""}" data-match-id="${match.match_id}">
      <h3 class="card-title">${match.title}</h3>
      <div class="card-meta">${match.subject_team_name}</div>
      <div class="tag-row">
        ${renderStatus(match.data_status)}
      </div>
      ${renderTags(match.focus_areas)}
    </button>
  `;
}

function renderTeamStyle(style) {
  if (!style.windows?.length) {
    teamStyleEl.innerHTML = `
      <article class="detail-card empty-state">
        <h3>No historical windows yet</h3>
        <p>Run the team window job after computing team match metrics to build season and competition style profiles.</p>
      </article>
    `;
    return;
  }

  teamStyleEl.innerHTML = `
    <div class="section-head">
      <h3>Team Style</h3>
      <span class="pill ${style.data_status === "ready" ? "" : "muted"}">${style.data_status.replace("_", " ")}</span>
    </div>
    <div class="window-list">
      ${style.windows
        .map(
          (window) => `
            <article class="window-card">
              <div class="window-head">
                <div>
                  <h4 class="window-title">${window.label}</h4>
                  <p class="window-meta">${window.match_count} match${window.match_count === 1 ? "" : "es"}${window.date_range_label ? ` - ${window.date_range_label}` : ""}</p>
                </div>
                <span class="tag">${window.window_type.replace("_", " ")}</span>
              </div>
              ${renderCompactMetrics(window.metrics)}
            </article>
          `
        )
        .join("")}
    </div>
  `;
}

function renderDetail(match) {
  const takeaways = match.takeaways?.length
    ? `
      <div class="takeaway-list">
        ${match.takeaways
          .map(
            (item) => `
              <article class="takeaway">
                <h4>${item.title}</h4>
                <p class="detail-copy">${item.detail}</p>
                ${renderTags(item.evidence_keys || [])}
              </article>
            `
          )
          .join("")}
      </div>
    `
    : `<p class="detail-copy">No tactical takeaways generated yet.</p>`;

  detailEl.className = "detail-card";
  detailEl.innerHTML = `
    <h3>${match.title}</h3>
    <p class="detail-copy">
      Subject team: <strong>${match.subject_team_name}</strong>
    </p>
    <div class="tag-row">
      ${renderStatus(match.data_status)}
    </div>
    ${renderTags(match.focus_areas || [])}
    ${renderTags(match.chart_blocks || [])}
    ${renderMetrics(match.metrics || [])}
    ${takeaways}
  `;
}

async function loadTeams() {
  const teams = await fetchJson("/api/teams");
  teamsCountEl.textContent = `${teams.length} loaded`;
  teamsEl.innerHTML = teams.map(teamCard).join("");

  teamsEl.querySelectorAll("[data-team-slug]").forEach((button) => {
    button.addEventListener("click", async () => {
      activeTeamSlug = button.dataset.teamSlug;
      activeMatchId = null;
      await loadTeams();
      await loadMatches(activeTeamSlug);
    });
  });

  if (!activeTeamSlug && teams.length) {
    activeTeamSlug = teams[0].team_slug;
    await loadTeams();
    await loadMatches(activeTeamSlug);
  }
}

async function loadMatches(teamSlug) {
  const [payload, style] = await Promise.all([
    fetchJson(`/api/teams/${teamSlug}/matches`),
    fetchJson(`/api/teams/${teamSlug}/style`),
  ]);
  activeTeamEl.textContent = payload.team_name;
  renderTeamStyle(style);
  matchesEl.innerHTML = payload.matches.length
    ? payload.matches.map(matchCard).join("")
    : `<article class="detail-card empty-state"><h3>No matches yet</h3><p>This team exists, but no matches are available in the current database.</p></article>`;

  matchesEl.querySelectorAll("[data-match-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      activeMatchId = button.dataset.matchId;
      await loadMatches(activeTeamSlug);
      await loadMatch(activeMatchId);
    });
  });

  if (!activeMatchId && payload.matches.length) {
    activeMatchId = payload.matches[0].match_id;
    await loadMatches(activeTeamSlug);
    await loadMatch(activeMatchId);
  }
}

async function loadMatch(matchId) {
  const match = await fetchJson(`/api/matches/${matchId}`);
  activeMatchEl.textContent = match.subject_team_name;
  renderDetail(match);
}

async function boot() {
  try {
    await loadTeams();
  } catch (error) {
    detailEl.className = "detail-card empty-state";
    detailEl.innerHTML = `
      <h3>Preview unavailable</h3>
      <p>${error.message}</p>
    `;
  }
}

boot();

const teamsEl = document.getElementById("teams");
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
  const payload = await fetchJson(`/api/teams/${teamSlug}/matches`);
  activeTeamEl.textContent = payload.team_name;
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

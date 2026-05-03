<template>
  <div class="app-shell">
    <div class="app-shell__grain"></div>
    <header class="app-header">
      <div class="app-header__brand">
        <div class="app-header__stamp">TA</div>
        <div>
          <div class="app-header__title">Trip Atlas</div>
          <div class="app-header__subtitle">HelloAgents Intelligent Travel Companion</div>
        </div>
      </div>
      <div class="app-header__meta">
        <span class="meta-pill">Atlas Edition</span>
        <span class="meta-copy">Plan better routes, stays, budgets, and local moments.</span>
      </div>
    </header>

    <main class="app-main">
      <router-view />
    </main>

    <footer class="app-footer">
      <span>Designed for memorable trips, not generic itineraries.</span>
      <span>HelloAgents Travel Planner</span>
    </footer>
  </div>
</template>

<script setup lang="ts">
</script>

<style>
:root {
  --atlas-bg: #f4ede2;
  --atlas-paper: #fbf6ee;
  --atlas-paper-strong: rgba(255, 252, 247, 0.95);
  --atlas-ink: #15313a;
  --atlas-muted: #6c7d83;
  --atlas-line: rgba(21, 49, 58, 0.14);
  --atlas-accent: #d46d3d;
  --atlas-accent-soft: rgba(212, 109, 61, 0.12);
  --atlas-deep: #1f5a5a;
  --atlas-shadow: 0 24px 60px rgba(45, 63, 71, 0.12);
}

html,
body,
#app {
  min-height: 100%;
}

body {
  margin: 0;
  background:
    radial-gradient(circle at top left, rgba(212, 109, 61, 0.18), transparent 30%),
    radial-gradient(circle at top right, rgba(31, 90, 90, 0.14), transparent 24%),
    linear-gradient(180deg, #f5efe5 0%, #efe8dc 55%, #edf0ea 100%);
  color: var(--atlas-ink);
  font-family: 'Avenir Next', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

* {
  box-sizing: border-box;
}

button,
input,
textarea,
select {
  font: inherit;
}

a {
  color: inherit;
  text-decoration: none;
}

.app-shell {
  min-height: 100vh;
  position: relative;
  overflow: hidden;
}

.app-shell__grain {
  position: fixed;
  inset: 0;
  pointer-events: none;
  opacity: 0.22;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.18) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.16) 1px, transparent 1px);
  background-size: 42px 42px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.9), rgba(0, 0, 0, 0.45));
}

.app-header,
.app-main,
.app-footer {
  position: relative;
  z-index: 1;
  max-width: 1480px;
  margin: 0 auto;
  padding-left: 24px;
  padding-right: 24px;
}

.app-header {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: center;
  padding-top: 22px;
  padding-bottom: 18px;
}

.app-header__brand {
  display: flex;
  align-items: center;
  gap: 14px;
}

.app-header__stamp {
  width: 50px;
  height: 50px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--atlas-deep), #2c7c77);
  color: #fffdf8;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.04em;
  box-shadow: 0 18px 28px rgba(31, 90, 90, 0.2);
}

.app-header__title,
.app-header__subtitle,
.app-header__meta,
.app-footer {
  line-height: 1.2;
}

.app-header__title {
  font-family: Georgia, 'Times New Roman', 'Songti SC', serif;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.app-header__subtitle {
  margin-top: 4px;
  color: var(--atlas-muted);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.app-header__meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.meta-pill {
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid var(--atlas-line);
  background: rgba(255, 255, 255, 0.55);
  font-size: 12px;
  font-weight: 700;
  color: var(--atlas-deep);
}

.meta-copy {
  color: var(--atlas-muted);
  font-size: 13px;
}

.app-main {
  padding-bottom: 22px;
}

.app-footer {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding-top: 8px;
  padding-bottom: 26px;
  color: var(--atlas-muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

@media (max-width: 900px) {
  .app-header,
  .app-footer {
    flex-direction: column;
    align-items: flex-start;
  }

  .app-header__meta {
    justify-content: flex-start;
  }
}

@media (max-width: 640px) {
  .app-header,
  .app-main,
  .app-footer {
    padding-left: 14px;
    padding-right: 14px;
  }

  .app-header {
    padding-top: 16px;
  }
}
</style>

// forge.js — small interactions for the broadsheet.
// Keep it lean: HTMX handles fetches; this file is just key shortcuts and one tiny chart.

(function () {
  // Cmd/Ctrl+Enter inside the SQL textarea fires the run button.
  document.addEventListener('keydown', function (e) {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      const ta = document.querySelector('textarea[name="sql"]');
      if (ta && document.activeElement === ta) {
        const form = ta.closest('form');
        if (form) form.requestSubmit();
        e.preventDefault();
      }
    }
  });

  // Schema-tree click behavior, tuned to actual workflow:
  //
  //   * If the editor still holds a query "we own" — either the
  //     server-rendered placeholder, or one we generated from a prior
  //     click — replace the whole buffer with a working
  //     `SELECT * FROM <fqn> LIMIT 100`. Lets you switch tables with
  //     a single click.
  //   * If you've actually typed in the editor since, clicks do an
  //     insert-at-cursor at the last position you left.
  let savedStart = null, savedEnd = null;
  let bufferIsOurs = true;   // becomes false the moment the user types

  function rememberCursor(ta) {
    savedStart = ta.selectionStart;
    savedEnd = ta.selectionEnd;
  }
  function isSqlTextarea(el) {
    return el && el.matches && el.matches('textarea[name="sql"]');
  }
  ['keyup', 'mouseup', 'focusin', 'select'].forEach((ev) => {
    document.addEventListener(ev, (e) => {
      if (isSqlTextarea(e.target)) rememberCursor(e.target);
    });
  });
  // The 'input' event fires on user typing/paste/cut but not on
  // programmatic `ta.value = ...`, so we can use it as a clean signal
  // that the buffer is no longer ours to overwrite.
  document.addEventListener('input', (e) => {
    if (isSqlTextarea(e.target)) bufferIsOurs = false;
  });
  // If the user landed here via "Open in Workbench" (?seed=...),
  // treat the URL-supplied query as their content from the start.
  document.addEventListener('DOMContentLoaded', () => {
    if (new URL(window.location.href).searchParams.has('seed')) {
      bufferIsOurs = false;
    }
  });

  document.addEventListener('click', function (e) {
    const t = e.target.closest('.schema-tree .tbl');
    if (!t) return;
    const ta = document.querySelector('textarea[name="sql"]');
    if (!ta) return;
    const fqn = t.dataset.fqn;

    if (bufferIsOurs) {
      const seed = `SELECT *\nFROM ${fqn}\nLIMIT 100`;
      ta.value = seed;
      bufferIsOurs = true;
      ta.focus();
      ta.selectionStart = ta.selectionEnd = seed.length;
      rememberCursor(ta);
      return;
    }

    const start = savedStart !== null ? savedStart : ta.value.length;
    const end   = savedEnd   !== null ? savedEnd   : ta.value.length;
    ta.value = ta.value.slice(0, start) + fqn + ta.value.slice(end);
    ta.focus();
    ta.selectionStart = ta.selectionEnd = start + fqn.length;
    rememberCursor(ta);
  });

  // Sparkline drawer for refusal-rate / latency history.
  // Looks for <canvas data-sparkline="comma,sep,values" data-color="#xxxxxx">.
  function drawSparklines() {
    document.querySelectorAll('canvas[data-sparkline]').forEach((c) => {
      const vals = c.dataset.sparkline.split(',').map(parseFloat).filter(v => !isNaN(v));
      if (!vals.length) return;
      const w = c.width, h = c.height;
      const ctx = c.getContext('2d');
      ctx.clearRect(0, 0, w, h);
      const min = Math.min(...vals), max = Math.max(...vals);
      const range = (max - min) || 1;
      const pad = 2;
      ctx.lineWidth = 1.4;
      ctx.strokeStyle = c.dataset.color || '#6b1422';
      ctx.beginPath();
      vals.forEach((v, i) => {
        const x = pad + (i / (vals.length - 1 || 1)) * (w - pad * 2);
        const y = h - pad - ((v - min) / range) * (h - pad * 2);
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      });
      ctx.stroke();
      // last-point dot
      const lx = w - pad, ly = h - pad - ((vals[vals.length - 1] - min) / range) * (h - pad * 2);
      ctx.fillStyle = c.dataset.color || '#6b1422';
      ctx.beginPath(); ctx.arc(lx, ly, 2.2, 0, Math.PI * 2); ctx.fill();
    });
  }
  document.addEventListener('DOMContentLoaded', drawSparklines);
  document.body.addEventListener('htmx:afterSwap', drawSparklines);
})();

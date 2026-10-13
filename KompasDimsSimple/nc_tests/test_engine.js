// Регрессионные проверки расчёта времени nc_checker.html (ручной счёт).
// Запуск: npm i playwright && node nc_tests/test_engine.js
const path = require('path');
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage(); const errs = [];
  p.on('pageerror', (e) => errs.push(e.message)); p.on('dialog', (d) => d.dismiss());
  await p.goto('file://' + path.resolve(__dirname, '..', 'nc_checker.html'));
  const cases = await p.evaluate(() => {
    const P = defaultParams(); P.model_spindle_ramp = false; P.m_codes.default_exec_time_ms = 0; P.t_code_exec_time_ms = 0;
    P.rapid_override_pct = 100;
    for (const a in P.axes) { P.axes[a].g0_accel_ms = 0; P.axes[a].g1_accel_ms = 0; P.axes[a].feed_clamp_mm_min = 1e9; }
    const run = (text, subs) => { const s = new Simulator(JSON.parse(JSON.stringify(P)), { mainSpindle: '1', subprograms: subs || {} }, 'T'); s.run(text); return s; };
    return [
      ['G0 X100 Z60 (30 м/мин)', run('G0X100.Z60.').segMs, 120],
      ['G99 подача на оборот, S1=', run('S1=1000M3\nG99G1Z-10.F0.1').segMs, 6000],
      ['G99 подача на оборот, обычное S', run('G97S1000M3\nG99G1Z-10.F0.1').segMs, 6000],
      ['G98 подача в минуту', run('G98G1Z-10.F100.').segMs, 6000],
      ['G04 X/P', run('G4X1.5\nG4P500').segMs, 2000],
      ['фаска ,C не двигает ось C', run('G98G1Z-10.,C1.F100.').pos.C, 0],
      ['цикл IF…GOTO назад со счётчиком', run('#1=0\nN10G98G1W-10.F100.\n#1=#1+1\nIF[#1LT3]GOTO10\nM30').segMs, 18000],
      ['WHILE/END', run('#1=0\nWHILE[#1LT3]DO1\nG98G1W-10.F100.\n#1=#1+1\nEND1\nM30').segMs, 18000],
      ['M98 L3', run('M98P100L3\nM30', { '100': 'G98G1W-10.F100.\nM99' }).segMs, 18000],
      ['IF THEN при ложном условии', run('#1=0\nIF[#1EQ1]THEN#2=5').vars['2'] === undefined ? 1 : 0, 1],
      ['дуга R10 90°', +run('G98G0X0Z0\nG2X20.Z-10.R10.F100.').segMs.toFixed(1), 9424.8],
      ['G96 на Ø50 (подвод 50 мс + 9424.8)', +run('G0X50.Z0\nG96S1=100M3\nG99G1Z-10.F0.1').segMs.toFixed(1), 9474.8],
      ['G76 проходы (0.774/0.15, m3, d0.1)', Simulator.threadPasses(0.774, 0.15, 3, 0.15, 0.1), 8],
      ['G76 проходы (0.774/0.65, m1, d0.1)', Simulator.threadPasses(0.774, 0.65, 1, 0.65, 0.1), 3],
    ];
  });
  let bad = 0;
  for (const [name, got, want] of cases) {
    const ok = Math.abs(got - want) < 0.05; if (!ok) bad++;
    console.log((ok ? 'OK   ' : 'FAIL ') + name + ': ' + got + (ok ? '' : ' (ожидалось ' + want + ')'));
  }
  if (errs.length) { bad++; console.log('Ошибки страницы:', errs); }
  await b.close(); process.exit(bad ? 1 : 0);
})();

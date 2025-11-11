window.onload = () => {
  const timeDisplay = document.getElementById('time-display');
  const currentModeDisplay = document.getElementById('current-mode-display');
  const startPauseButton = document.getElementById('start-pause-button');
  const resetButton = document.getElementById('reset-button');
  const pomodoroCountDisplay = document.getElementById('pomodoro-count');
  const timerVisualContainer = document.getElementById(
    'timer-visual-container'
  );

  const pomodoroModeButton = document.getElementById('pomodoro-mode');
  const shortBreakModeButton = document.getElementById('short-break-mode');
  const longBreakModeButton = document.getElementById('long-break-mode');

  const progressCircle = document.getElementById('progress-ring-circle');
  const radius = progressCircle.r.baseVal.value;
  const circumference = 2 * Math.PI * radius;
  progressCircle.style.strokeDasharray = `${circumference} ${circumference}`;
  progressCircle.style.strokeDashoffset = 0;

  let synth = null; // Initialize synth as null

  const timerModes = {
    pomodoro: 25 * 60,
    shortBreak: 5 * 60,
    longBreak: 15 * 60,
  };

  let timerInterval = null;
  let currentMode = 'pomodoro';
  let timeLeft = timerModes[currentMode];
  let isRunning = false;
  let pomodoroCount = 0;

  function updateDisplay() {
    const minutes = Math.floor(timeLeft / 60);
    const seconds = timeLeft % 60;
    const formattedTime = `${String(minutes).padStart(2, '0')}:${String(
      seconds
    ).padStart(2, '0')}`;
    timeDisplay.textContent = formattedTime;
    document.title = `${formattedTime} - Focus Timer`;

    const totalTime = timerModes[currentMode];
    const offset = circumference - (timeLeft / totalTime) * circumference;
    progressCircle.style.strokeDashoffset = offset;
  }

  function switchMode(newMode) {
    currentMode = newMode;
    timeLeft = timerModes[currentMode];
    pauseTimer();
    updateDisplay();
    updateActiveButton();

    let modeText = 'Focus';
    if (newMode === 'shortBreak') modeText = 'Short Break';
    if (newMode === 'longBreak') modeText = 'Long Break';
    currentModeDisplay.textContent = modeText;
  }

  function updateActiveButton() {
    document
      .querySelectorAll('.mode-button')
      .forEach((button) => button.classList.remove('active'));
    if (currentMode === 'pomodoro') pomodoroModeButton.classList.add('active');
    else if (currentMode === 'shortBreak')
      shortBreakModeButton.classList.add('active');
    else if (currentMode === 'longBreak')
      longBreakModeButton.classList.add('active');
  }

  function startTimer() {
    if (isRunning) return;

    if (typeof Tone !== 'undefined') {
      if (!synth) {
        synth = new Tone.Synth().toDestination();
      }
      if (Tone.context.state !== 'running') {
        Tone.start();
      }
    }

    isRunning = true;
    startPauseButton.textContent = 'PAUSE';
    timerVisualContainer.classList.add('timer-running');

    timerInterval = setInterval(() => {
      timeLeft--;
      updateDisplay();
      if (timeLeft <= 0) {
        handleTimerEnd();
      }
    }, 1000);
  }

  function pauseTimer() {
    isRunning = false;
    startPauseButton.textContent = 'START';
    timerVisualContainer.classList.remove('timer-running');
    clearInterval(timerInterval);
  }

  function resetTimer() {
    pauseTimer();
    timeLeft = timerModes[currentMode];
    updateDisplay();
  }

  function handleTimerEnd() {
    pauseTimer();
    if (synth) {
      synth.triggerAttackRelease('C5', '0.2');
      setTimeout(() => synth.triggerAttackRelease('G5', '0.3'), 200);
    }

    if (currentMode === 'pomodoro') {
      pomodoroCount++;
      pomodoroCountDisplay.textContent = pomodoroCount;
      if (pomodoroCount > 0 && pomodoroCount % 4 === 0) {
        switchMode('longBreak');
      } else {
        switchMode('shortBreak');
      }
    } else {
      switchMode('pomodoro');
    }
  }

  startPauseButton.addEventListener('click', () => {
    if (isRunning) {
      pauseTimer();
    } else {
      startTimer();
    }
  });

  resetButton.addEventListener('click', resetTimer);
  pomodoroModeButton.addEventListener('click', () => switchMode('pomodoro'));
  shortBreakModeButton.addEventListener('click', () =>
    switchMode('shortBreak')
  );
  longBreakModeButton.addEventListener('click', () => switchMode('longBreak'));

  // Initial setup
  updateDisplay();
  updateActiveButton();
};
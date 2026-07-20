/**
 * Audio Interview System
 * Interactive interview system for collecting comprehensive user information
 * Uses speech recognition, TTS, and AI-powered follow-up questions
 */

class AudioInterviewSystem {
    constructor() {
        this.isActive = false;
        this.isPaused = false;
        this.currentQuestionIndex = 0;
        this.interviewData = {
            userName: '',
            responses: [],
            friendsFamily: [],
            startTime: null,
            lastSaveTime: null
        };
        
        // Speech recognition
        this.recognition = null;
        this.isListening = false;
        this.currentRecognizedText = '';
        this.accumulatedText = ''; // Initialize accumulated text for multi-pause responses
        
        // TTS
        this.ttsEnabled = true;
        this.currentUtterance = null;
        
        // Question asking state
        this.isAskingQuestion = false;
        this.shouldStopListening = false;
        
        // Question management - Use comprehensive questions from interview-questions.js
        this.baseQuestions = [];
        this.loadComprehensiveQuestions();

        this.loadComprehensiveQuestions();
        
        this.currentQuestions = [...this.baseQuestions];
        this.additionalQuestions = [];
        
        this.initializeElements();
        this.setupEventListeners();
        this.initializeSpeechRecognition();
        
        // Load any saved interview progress
        this.loadSavedProgress();
        
        console.log('AudioInterviewSystem initialized successfully');
    }

    loadComprehensiveQuestions() {
        // Check if INTERVIEW_QUESTIONS is available from interview-questions.js
        if (typeof window.INTERVIEW_QUESTIONS !== 'undefined') {
            this.baseQuestions = this.convertComprehensiveQuestions(window.INTERVIEW_QUESTIONS);
        } else {
            // Fallback to basic questions if comprehensive questions aren't loaded
            console.warn('INTERVIEW_QUESTIONS not found, using fallback questions');
            this.baseQuestions = [
                {
                    id: 'user_name',
                    text: "What is the name of the person who will be using this application?",
                    type: 'identity',
                    required: true,
                    followUp: true
                },
                {
                    id: 'user_info',
                    text: "Can you tell me about this person - their interests, personality, and what's important to know about them?",
                    type: 'general',
                    required: true,
                    followUp: true
                }
            ];
        }
        
        this.currentQuestions = [...this.baseQuestions];
        this.additionalQuestions = [];
    }

    convertComprehensiveQuestions(interviewQuestions) {
        const convertedQuestions = [];
        
        // Convert the comprehensive question structure to the format expected by the audio system
        Object.keys(interviewQuestions).forEach(categoryKey => {
            if (categoryKey === 'INTERVIEW_CONFIG') return; // Skip config
            
            const categoryQuestions = interviewQuestions[categoryKey];
            categoryQuestions.forEach(questionObj => {
                convertedQuestions.push({
                    id: questionObj.id,
                    text: questionObj.question,
                    type: questionObj.category,
                    required: questionObj.required || false,
                    followUp: false,
                    followUpQuestion: questionObj.followUp
                });
            });
        });
        
        return convertedQuestions;
    }

    initializeElements() {
        // Modal elements
        this.modal = document.getElementById('audioInterviewModal');
        this.startInterviewButton = document.getElementById('startInterviewButton');
        this.closeInterviewModal = document.getElementById('closeInterviewModal');
        this.closeInterviewBtn = document.getElementById('closeInterviewBtn');
        
        // Interview control elements
        this.startInterviewBtn = document.getElementById('startInterviewBtn');
        this.pauseResumeBtn = document.getElementById('pauseResumeBtn');
        this.repeatQuestionBtn = document.getElementById('repeatQuestionBtn');
        this.prevQuestionBtn = document.getElementById('prevQuestionBtn');
        
        // Status and progress elements
        this.interviewStatus = document.getElementById('interviewStatus');
        this.interviewProgress = document.getElementById('interviewProgress');
        this.currentQuestion = document.getElementById('currentQuestion');
        this.interviewLog = document.getElementById('interviewLog');
        
        // Answer input elements
        this.answerInputArea = document.getElementById('answerInputArea');
        this.answerTextarea = document.getElementById('interviewAnswerText');
        this.birthdayDateInput = document.getElementById('birthdayDateInput');
        this.dictateBtn = document.getElementById('dictateBtn');
        this.dictateStatus = document.getElementById('dictateStatus');
        this.submitAnswerBtn = document.getElementById('submitAnswerBtn');
        this.clearAnswerBtn = document.getElementById('clearAnswerBtn');

        // Legacy voice recognition elements (kept for backward-compat with user_info_admin)
        this.voiceRecognitionFeedback = document.getElementById('voiceRecognitionFeedback');
        this.recognizedText = document.getElementById('recognizedText');
        this.confirmResponseBtn = document.getElementById('confirmResponseBtn');
        this.retryResponseBtn = document.getElementById('retryResponseBtn');
        
        // Action buttons
        this.restartInterviewBtn = document.getElementById('restartInterviewBtn');
        this.generateNarrativeBtn = document.getElementById('generateNarrativeBtn');
        this.closeInterviewModalBtn = document.getElementById('closeInterviewModal');
    }

    setupEventListeners() {
        // Helper: removes any handler a previous instance registered on this element,
        // then attaches the new one. Stores the handler on the element so it can be
        // cleaned up if another instance is created later.
        const on = (el, event, handler, key) => {
            if (!el) return;
            const prop = `_ais_${key || event}`;
            if (el[prop]) el.removeEventListener(event, el[prop]);
            el[prop] = handler;
            el.addEventListener(event, handler);
        };

        // Modal controls
        on(this.startInterviewButton, 'click', () => this.openInterviewModal(), 'openModal');
        on(this.closeInterviewModalBtn, 'click', () => this.handleCloseModal(), 'closeModal');
        on(this.closeInterviewBtn, 'click', () => this.handleCloseModal(), 'closeInterview');

        // Interview controls
        on(this.startInterviewBtn, 'click', () => this.startInterview(), 'start');
        on(this.pauseResumeBtn, 'click', () => this.togglePauseResume(), 'pause');
        on(this.repeatQuestionBtn, 'click', () => this.repeatCurrentQuestion(), 'repeat');
        on(this.prevQuestionBtn, 'click', () => this.previousQuestion(), 'prev');

        // Answer input controls
        on(this.submitAnswerBtn, 'click', () => this.confirmCurrentResponse(), 'submit');
        on(this.dictateBtn, 'click', () => this.toggleDictation(), 'dictate');
        on(this.clearAnswerBtn, 'click', () => this.clearCurrentAnswer(), 'clear');

        // Legacy voice recognition controls
        on(this.confirmResponseBtn, 'click', () => this.confirmCurrentResponse(), 'confirmResp');
        on(this.retryResponseBtn, 'click', () => this.retryVoiceRecognition(), 'retry');

        // Action buttons
        on(this.restartInterviewBtn, 'click', () => this.restartInterview(), 'restart');
        on(this.generateNarrativeBtn, 'click', () => this.generateAndSaveNarrative(), 'generate');

        // Escape key — remove any prior keydown handler this class registered
        if (document._ais_keydown) document.removeEventListener('keydown', document._ais_keydown);
        document._ais_keydown = (e) => {
            if (e.key === 'Escape' && this.modal && !this.modal.classList.contains('hidden')) {
                this.closeInterviewModal();
            }
        };
        document.addEventListener('keydown', document._ais_keydown);
    }

    initializeSpeechRecognition() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            console.warn('Speech recognition not supported in this browser');
            this.updateStatus('Speech recognition not available. Please use Chrome/Edge for best experience.', 'warning');
            return;
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();

        // continuous=true keeps the session alive as long as possible.
        // We do NOT auto-restart in onend — when the browser ends the session the
        // button simply reverts to "Dictate" so the user can click again if needed.
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';

        this.recognition.onstart = () => {
            this.isListening = true;
            this._dictateSessionStart = Date.now();
            if (this.dictateStatus) {
                this.dictateStatus.textContent = 'Listening…';
                this.dictateStatus.classList.remove('hidden');
            }
            this.updateStatus('Listening — speak your answer…', 'listening');
        };

        this.recognition.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                } else {
                    interimTranscript += transcript;
                }
            }

            if (finalTranscript.trim()) {
                const sep = (this.accumulatedText && this.accumulatedText.trim()) ? ' ' : '';
                this.accumulatedText = (this.accumulatedText || '') + sep + finalTranscript.trim();
            }

            const displayText = this.accumulatedText
                ? this.accumulatedText + (interimTranscript.trim() ? ' ' + interimTranscript.trim() : '')
                : interimTranscript.trim();

            this.currentRecognizedText = displayText;

            if (this.answerTextarea) {
                this.answerTextarea.value = displayText;
            } else if (this.recognizedText) {
                this.recognizedText.textContent = displayText || '(Listening…)';
                if (finalTranscript.length > 0 || interimTranscript.length > 0) {
                    this.confirmResponseBtn?.classList.remove('hidden');
                    this.retryResponseBtn?.classList.remove('hidden');
                }
            }
        };

        this.recognition.onerror = (event) => {
            this.isListening = false;
            if (event.error === 'aborted') return;
            if (event.error === 'not-allowed') {
                this.updateStatus('Microphone access denied. Please allow microphone access and try again.', 'error');
                this._stopDictation();
                return;
            }
            if (event.error !== 'no-speech') {
                console.warn('[DICTATION] Recognition error:', event.error);
            }
            // For no-speech or other errors, onend will follow and stop cleanly
        };

        this.recognition.onend = () => {
            this.isListening = false;
            // Session ended — stop dictation mode. Text already captured stays in the textarea.
            // If it ended unusually fast (< 400ms) and we were still actively trying to
            // dictate, show a hint so the user knows to try again.
            const sessionMs = Date.now() - (this._dictateSessionStart || 0);
            if (this.isDictating && sessionMs < 400) {
                this._stopDictation();
                this.updateStatus('Microphone stopped early — click Dictate to try again.', 'warning');
            } else {
                this._stopDictation();
            }
        };
    }

    async openInterviewModal() {
        // When launched from the setup wizard always start completely fresh
        if (sessionStorage.getItem('wizardInterviewMode') === '1') {
            this._resetState();
        }

        this.modal.classList.remove('hidden');
        this.updateProgress();

        // Load responses from Firestore (authoritative source) unless this is a fresh wizard run
        if (sessionStorage.getItem('wizardInterviewMode') !== '1') {
            await this._loadResponsesFromFirestore();
        }

        if (this.interviewData.responses.length > 0) {
            this.currentQuestion.textContent = `Welcome back! You have ${this.interviewData.responses.length} responses saved. Click "Start Interview" to review and edit answers, or "Restart Interview" to start fresh.`;
            this.generateNarrativeBtn?.classList.remove('hidden');
        }
    }

    _resetState() {
        this.isActive = false;
        this.isPaused = false;
        this.currentQuestionIndex = 0;
        this._submitting = false;
        this.interviewData = { userName: '', responses: [], friendsFamily: [], startTime: null, lastSaveTime: null };
        this.currentQuestions = [...this.baseQuestions];
        this.accumulatedText = '';
        this.currentRecognizedText = '';
        this.isDictating = false;
        this.shouldStopListening = false;
        this.clearSavedProgress();

        // Reset UI
        if (this.interviewLog) this.clearInterviewLog();
        if (this.currentQuestion) this.currentQuestion.textContent = 'Welcome! I\'ll ask you some questions to learn about this user. Click "Start Interview" when you\'re ready.';
        this.startInterviewBtn?.classList.remove('hidden');
        this.pauseResumeBtn?.classList.add('hidden');
        this.prevQuestionBtn?.classList.add('hidden');
        this.generateNarrativeBtn?.classList.add('hidden');
        if (this.answerInputArea) this.answerInputArea.classList.add('hidden');
        if (this.submitAnswerBtn) {
            this.submitAnswerBtn.disabled = false;
            this.submitAnswerBtn.innerHTML = 'Next Question <i class="fas fa-arrow-right ml-1"></i>';
        }
        if (this.birthdayDateInput) {
            this.birthdayDateInput.value = '';
            this.birthdayDateInput.classList.add('hidden');
        }
        if (this.answerTextarea) this.answerTextarea.classList.remove('hidden');
    }

    async handleCloseModal() {
        const fromWizard = sessionStorage.getItem('wizardInterviewMode') === '1';

        try {
            this.closeInterviewModal();
        } catch (error) {
            console.error('Error in handleCloseModal:', error);
            const modal = document.getElementById('audioInterviewModal');
            if (modal) { modal.style.display = 'none'; modal.classList.add('hidden'); }
        }

        // If launched from the setup wizard, save answers and go to the selected interface
        if (fromWizard) {
            sessionStorage.removeItem('wizardInterviewMode');
            await this._saveResponsesToFirestore();
            try {
                const prefResp = await window.authenticatedFetch('/api/interface-preference', { method: 'GET' });
                const prefData = prefResp.ok ? await prefResp.json() : {};
                const target = prefData.useTapInterface ? 'tap_interface.html' : 'gridpage.html';
                window.location.href = `${target}?page=home`;
            } catch (e) {
                window.location.href = 'gridpage.html?page=home';
            }
        }
    }

    closeInterviewModal() {
        this.isActive = false;
        this.isPaused = false;
        this.stopListening();
        
        if (this.modal) {
            this.modal.style.display = 'none';
            this.modal.classList.add('hidden');
        }
        
        // Save progress locally and to Firestore
        this.saveProgress();
        this._saveResponsesToFirestore();
        
        // Clean up speech synthesis
        if (window.speechSynthesis) {
            window.speechSynthesis.cancel();
        }
    }

    async startInterview() {
        if (!this.isActive) {
            this.isActive = true;
            this.interviewData.startTime = new Date().toISOString();
            this.updateStatus('Interview started', 'success');
            
            // Show interview controls
            this.startInterviewBtn?.classList.add('hidden');
            this.pauseResumeBtn?.classList.remove('hidden');
            this.repeatQuestionBtn?.classList.remove('hidden');
        }

        this.isPaused = false;
        if (this.pauseResumeBtn) this.pauseResumeBtn.innerHTML = '<i class="fas fa-pause"></i> Pause';
        
        await this.askCurrentQuestion();
    }

    async askCurrentQuestion() {
        if (this.isPaused || !this.isActive) return;
        
        // Prevent duplicate calls
        if (this.isAskingQuestion) {
            console.log('Already asking a question, skipping duplicate call');
            return;
        }
        
        const question = this.getCurrentQuestion();
        if (!question) {
            await this.completeInterview();
            return;
        }
        
        this.isAskingQuestion = true;

        try {
            const questionText = this.processQuestionText(question.text);
            this.currentQuestion.textContent = questionText;
            this.updateProgress();
            this.addToInterviewLog(`Q${this.currentQuestionIndex + 1}: ${questionText}`, 'question');

            // Reset answer state
            this.accumulatedText = '';
            this.currentRecognizedText = '';
            this.shouldStopListening = false;
            this.isDictating = false;

            // Show answer input area and re-enable submit button
            if (this.answerInputArea) this.answerInputArea.classList.remove('hidden');

            // Pre-populate with previously saved answer if this question was already answered
            const existingResponse = this.interviewData.responses[this.currentQuestionIndex];
            if (this.answerTextarea) {
                this.answerTextarea.value = existingResponse ? existingResponse.answer : '';
            }
            if (this.submitAnswerBtn) {
                this.submitAnswerBtn.disabled = false;
                const isLastQuestion = this.currentQuestionIndex === this.currentQuestions.length - 1;
                this.submitAnswerBtn.innerHTML = isLastQuestion
                    ? 'Generate Profile <i class="fas fa-check ml-1"></i>'
                    : 'Next Question <i class="fas fa-arrow-right ml-1"></i>';
            }
            this._submitting = false;

            // Show date picker for birthday question, textarea for everything else
            const isBirthdayQuestion = question && question.id === 'user_birthday';
            if (this.answerTextarea) {
                this.answerTextarea.classList.toggle('hidden', isBirthdayQuestion);
                if (!isBirthdayQuestion) this.answerTextarea.focus();
            }
            if (this.birthdayDateInput) {
                this.birthdayDateInput.classList.toggle('hidden', !isBirthdayQuestion);
                if (isBirthdayQuestion) {
                    const savedBday = existingResponse ? existingResponse.answer : '';
                    this.birthdayDateInput.value = /^\d{4}-\d{2}-\d{2}$/.test(savedBday) ? savedBday : '';
                    this.birthdayDateInput.focus();
                }
            }
            if (isBirthdayQuestion && this.dictateBtn) this.dictateBtn.classList.add('hidden');
            if (!isBirthdayQuestion && this.dictateBtn) this.dictateBtn.classList.remove('hidden');

            if (this.dictateBtn) {
                this.dictateBtn.innerHTML = '<i class="fas fa-microphone mr-1"></i> Dictate';
                this.dictateBtn.classList.remove('bg-red-600', 'hover:bg-red-700');
                this.dictateBtn.classList.add('bg-gray-600', 'hover:bg-gray-700');
            }
            if (this.dictateStatus) {
                this.dictateStatus.textContent = '';
                this.dictateStatus.classList.add('hidden');
            }
            this.updateStatus('Read the question above and type or dictate your answer.', 'info');
        } finally {
            this.isAskingQuestion = false;
        }
    }

    getCurrentQuestion() {
        if (this.currentQuestionIndex < this.currentQuestions.length) {
            return this.currentQuestions[this.currentQuestionIndex];
        }
        return null;
    }

    processQuestionText(text) {
        const userName = this.interviewData.userName || 'the user';
        return text.replace(/\{userName\}/g, userName);
    }

    async speakText(text) {
        if (!this.ttsEnabled) return;
        
        return new Promise((resolve) => {
            // Stop any current speech
            if (this.currentUtterance) {
                speechSynthesis.cancel();
            }
            
            this.currentUtterance = new SpeechSynthesisUtterance(text);
            this.currentUtterance.rate = 0.9;
            this.currentUtterance.pitch = 1;
            this.currentUtterance.volume = 0.8;
            
            this.currentUtterance.onend = () => {
                resolve();
            };
            
            this.currentUtterance.onerror = () => {
                console.warn('TTS error');
                resolve();
            };
            
            speechSynthesis.speak(this.currentUtterance);
        });
    }

    stopTTS() {
        if (speechSynthesis.speaking) {
            speechSynthesis.cancel();
        }
        this.currentUtterance = null;
    }

    startListening() {
        if (!this.recognition) {
            this.updateStatus('Speech recognition not available', 'error');
            return;
        }
        
        // Stop any existing recognition first to prevent conflicts
        if (this.isListening) {
            this.recognition.stop();
            // Wait a moment for it to fully stop
            setTimeout(() => this.startListening(), 100);
            return;
        }
        
        // Initialize accumulated text for fresh start
        this.accumulatedText = '';
        this.currentRecognizedText = '';
        this.recognizedText.textContent = '(Listening...)';
        this.confirmResponseBtn.classList.add('hidden');
        
        try {
            this.recognition.start();
        } catch (error) {
            console.error('Error starting speech recognition:', error);
            // If already running, don't show error
            if (error.name !== 'InvalidStateError') {
                this.updateStatus('Could not start voice recognition', 'error');
            }
        }
    }

    continueListening() {
        if (!this.recognition) {
            this.updateStatus('Speech recognition not available', 'error');
            return;
        }
        
        console.log('[INTERVIEW DEBUG] Continue listening. Accumulated text:', this.accumulatedText);
        
        // Don't clear accumulated text - continue building on existing response
        this.currentRecognizedText = this.accumulatedText || '';
        this.recognizedText.textContent = this.currentRecognizedText || '(Listening...)';
        
        try {
            this.recognition.start();
        } catch (error) {
            console.error('Error continuing speech recognition:', error);
            this.updateStatus('Could not continue voice recognition', 'error');
        }
    }

    stopListening() {
        if (this.recognition && this.isListening) {
            this.recognition.stop();
        }
        this.showVoiceRecognitionFeedback(false);
    }

    showVoiceRecognitionFeedback(show) {
        if (!this.voiceRecognitionFeedback) return;
        if (show) {
            this.voiceRecognitionFeedback.classList.remove('hidden');
        } else {
            this.voiceRecognitionFeedback.classList.add('hidden');
        }
    }

    async confirmCurrentResponse() {
        // Guard against double-submit
        if (this._submitting) return;
        this._submitting = true;
        if (this.submitAnswerBtn) this.submitAnswerBtn.disabled = true;

        // Read from date input (birthday question) or textarea, fall back to speech-recognized text
        const currentQ = this.getCurrentQuestion();
        const isBirthdayQ = currentQ && currentQ.id === 'user_birthday';
        let answerText;
        if (isBirthdayQ && this.birthdayDateInput && this.birthdayDateInput.value) {
            answerText = this.birthdayDateInput.value.trim();
        } else {
            answerText = this.answerTextarea
                ? this.answerTextarea.value.trim()
                : (this.currentRecognizedText || '').trim();
        }


        // Stop any active dictation
        if (this.isDictating) {
            this.shouldStopListening = true;
            this.isDictating = false;
            if (this.recognition && this.isListening) this.recognition.stop();
            this._stopDictation();
        }
        this.shouldStopListening = true;

        // Clean up legacy UI if present
        this.confirmResponseBtn?.classList.add('hidden');
        this.retryResponseBtn?.classList.add('hidden');

        // Hide answer area while moving to next question
        if (this.answerInputArea) this.answerInputArea.classList.add('hidden');

        this.updateStatus('Saving response…', 'processing');

        const currentQuestion = this.getCurrentQuestion();
        if (!currentQuestion) {
            console.error('No current question available');
            this.updateStatus('Error: No question available', 'error');
            return;
        }

        const response = {
            questionId: currentQuestion.id,
            question: this.processQuestionText(currentQuestion.text),
            answer: answerText,
            timestamp: new Date().toISOString(),
            type: currentQuestion.type
        };
        
        // Special handling for user name
        if (currentQuestion.id === 'user_name') {
            this.interviewData.userName = answerText;
        }

        // Update in place if re-answering, otherwise append
        if (this.currentQuestionIndex < this.interviewData.responses.length) {
            this.interviewData.responses[this.currentQuestionIndex] = response;
        } else {
            this.interviewData.responses.push(response);
        }
        this.addToInterviewLog(`A${this.currentQuestionIndex + 1}: ${response.answer}`, 'answer');

        this.stopListening();

        // Check if we need follow-up questions
        if (currentQuestion.followUp) {
            await this.generateFollowUpQuestions(response);
        }

        this.currentQuestionIndex++;
        this._submitting = false;

        // Update Previous button visibility
        this._updatePrevBtn();

        const hasMoreQuestions = this.currentQuestionIndex < this.currentQuestions.length;
        if (!hasMoreQuestions) {
            await this.generateAndSaveNarrative();
        } else {
            setTimeout(async () => {
                if (this.isActive && !this.isPaused) {
                    await this.askCurrentQuestion();
                }
            }, 800);
        }
    }

    async generateFollowUpQuestions(response) {
        try {
            const prompt = `Based on this interview response about a user for an AAC application:

Question: ${response.question}
Answer: ${response.answer}

Generate 1-2 specific follow-up questions that would help gather more detailed information for their user profile. The questions should be:
- Specific and actionable
- Help understand preferences, habits, or important details
- Be natural conversation starters
- Focus on information that would help personalize their AAC experience

Return only the follow-up questions, one per line, without numbering or bullet points.`;

            const followUpResponse = await this.callLLM(prompt);
            
            if (followUpResponse && followUpResponse.trim()) {
                const questions = followUpResponse.split('\n').filter(q => q.trim().length > 10);
                
                questions.forEach(questionText => {
                    const followUpQuestion = {
                        id: `followup_${response.questionId}_${Date.now()}`,
                        text: questionText.trim(),
                        type: `${response.type}_followup`,
                        followUp: false
                    };
                    
                    // Insert follow-up questions after current question
                    this.currentQuestions.splice(this.currentQuestionIndex + 1, 0, followUpQuestion);
                });
            }
        } catch (error) {
            console.error('Error generating follow-up questions:', error);
        }
    }

    async callLLM(prompt) {
        if (typeof window.authenticatedFetch !== 'function') return '';
        try {
            const response = await window.authenticatedFetch('/llm', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    prompt: prompt
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                return data.response || '';
            } else {
                console.error('LLM API error:', response.status, response.statusText);
                const errorText = await response.text();
                console.error('Error details:', errorText);
                throw new Error(`LLM API returned ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            console.error('LLM call failed:', error);
        }
        return '';
    }

    toggleDictation() {
        if (this.isDictating) {
            // User clicked "Stop Dictating" — stop the session and revert the button
            this.isDictating = false;
            if (this.recognition && this.isListening) {
                this.recognition.stop(); // triggers onend → _stopDictation()
            } else {
                this._stopDictation(); // recognition already ended, clean up button
            }
        } else {
            if (!this.recognition) {
                this.updateStatus('Speech recognition is not available in this browser.', 'error');
                return;
            }
            // Preserve any text already typed; dictation appends to it
            const existing = this.answerTextarea ? this.answerTextarea.value.trim() : '';
            this.accumulatedText = existing;
            this.isDictating = true;
            if (this.dictateBtn) {
                this.dictateBtn.innerHTML = '<i class="fas fa-stop mr-1"></i> Stop Dictating';
                this.dictateBtn.classList.remove('bg-gray-600', 'hover:bg-gray-700');
                this.dictateBtn.classList.add('bg-red-600', 'hover:bg-red-700');
            }
            if (this.dictateStatus) {
                this.dictateStatus.textContent = 'Starting…';
                this.dictateStatus.classList.remove('hidden');
            }
            try {
                this.recognition.start();
            } catch (e) {
                console.warn('[DICTATION] Could not start recognition:', e);
                this._stopDictation();
            }
        }
    }

    _stopDictation() {
        this.isDictating = false;
        if (this.dictateBtn) {
            this.dictateBtn.innerHTML = '<i class="fas fa-microphone mr-1"></i> Dictate';
            this.dictateBtn.classList.remove('bg-red-600', 'hover:bg-red-700');
            this.dictateBtn.classList.add('bg-gray-600', 'hover:bg-gray-700');
        }
        if (this.dictateStatus) {
            this.dictateStatus.textContent = '';
            this.dictateStatus.classList.add('hidden');
        }
        this.updateStatus('Read the question above and type or dictate your answer.', 'info');
    }

    retryVoiceRecognition() {
        this.stopListening();
        this.shouldStopListening = false;
        this.accumulatedText = '';
        this.currentRecognizedText = '';
        this.confirmResponseBtn?.classList.add('hidden');
        this.retryResponseBtn?.classList.add('hidden');
        setTimeout(() => { this.startListening(); }, 500);
    }

    clearCurrentAnswer() {
        if (this.answerTextarea) this.answerTextarea.value = '';
        if (this.birthdayDateInput) this.birthdayDateInput.value = '';
        if (this.answerTextarea && !this.answerTextarea.classList.contains('hidden')) {
            this.answerTextarea.focus();
        }
    }

    async previousQuestion() {
        if (this.currentQuestionIndex <= 0) return;
        this.stopListening();
        if (this.isDictating) { this.isDictating = false; this._stopDictation(); }

        this.currentQuestionIndex--;
        this._updatePrevBtn();
        // askCurrentQuestion() will pre-populate from responses[currentQuestionIndex]
        await this.askCurrentQuestion();
    }

    _updatePrevBtn() {
        if (!this.prevQuestionBtn) return;
        if (this.currentQuestionIndex > 0) {
            this.prevQuestionBtn.classList.remove('hidden');
        } else {
            this.prevQuestionBtn.classList.add('hidden');
        }
    }

    skipCurrentQuestion() {
        this.stopListening();
        if (this.isDictating) { this.isDictating = false; this._stopDictation(); }
        if (this.answerInputArea) this.answerInputArea.classList.add('hidden');
        this.addToInterviewLog(`Q${this.currentQuestionIndex + 1}: Skipped`, 'skipped');
        this.currentQuestionIndex++;
        
        setTimeout(async () => {
            if (this.isActive && !this.isPaused) {
                await this.askCurrentQuestion();
            }
        }, 500);
    }

    async repeatCurrentQuestion() {
        this.stopListening();
        await this.askCurrentQuestion();
    }

    togglePauseResume() {
        this.isPaused = !this.isPaused;
        
        if (this.isPaused) {
            this.stopListening();
            this.stopTTS();
            if (this.pauseResumeBtn) this.pauseResumeBtn.innerHTML = '<i class="fas fa-play"></i> Resume';
            this.updateStatus('Interview paused', 'warning');
        } else {
            if (this.pauseResumeBtn) this.pauseResumeBtn.innerHTML = '<i class="fas fa-pause"></i> Pause';
            this.updateStatus('Interview resumed', 'success');
            setTimeout(async () => {
                await this.askCurrentQuestion();
            }, 1000);
        }
    }

    async completeInterview() {
        this.isActive = false;
        this.stopListening();
        this.stopTTS();

        this.updateStatus('Interview completed!', 'success');
        this.currentQuestion.textContent = 'Interview completed! You can now generate the user profile or review your responses.';

        // Hide answer input and interview controls, show generate button
        if (this.answerInputArea) this.answerInputArea.classList.add('hidden');
        this.pauseResumeBtn?.classList.add('hidden');
        this.repeatQuestionBtn?.classList.add('hidden');
        this.prevQuestionBtn?.classList.add('hidden');
        this.generateNarrativeBtn?.classList.remove('hidden');
        
        // Auto-save progress
        await this.saveProgress();
    }

    async restartInterview() {
        if (confirm('Are you sure you want to restart the interview? All progress will be lost.')) {
            this.isActive = false;
            this.isPaused = false;
            this.currentQuestionIndex = 0;
            this.interviewData = {
                userName: '',
                responses: [],
                friendsFamily: [],
                startTime: null,
                lastSaveTime: null
            };
            this.currentQuestions = [...this.baseQuestions];
            
            this.clearInterviewLog();
            this.clearSavedProgress();
            this.updateProgress();
            
            // Reset UI
            this.startInterviewBtn?.classList.remove('hidden');
            this.pauseResumeBtn?.classList.add('hidden');
            this.repeatQuestionBtn?.classList.add('hidden');
            this.generateNarrativeBtn?.classList.add('hidden');
            if (this.answerInputArea) this.answerInputArea.classList.add('hidden');
            this.showVoiceRecognitionFeedback(false);
            
            this.currentQuestion.textContent = "Interview restarted. Click 'Start Interview' when you're ready to begin.";
            this.updateStatus('Ready to start interview', 'info');
        }
    }

    async generateAndSaveNarrative() {
        if (this.interviewData.responses.length === 0) {
            alert('No interview responses to process. Please complete the interview first.');
            return;
        }
        
        this.updateStatus('Generating user profile narrative...', 'processing');
        
        try {
            const narrative = await this.generateNarrative();
            await this.populateUserInfoFields(narrative);
            
            this.updateStatus('User profile generated and saved successfully!', 'success');

            // If launched from the setup wizard, go straight to the home page
            if (sessionStorage.getItem('wizardInterviewMode') === '1') {
                sessionStorage.removeItem('wizardInterviewMode');
                this.updateStatus('Profile saved! Taking you to the app…', 'success');
                setTimeout(async () => {
                    try {
                        const prefResp = await window.authenticatedFetch('/api/interface-preference', { method: 'GET' });
                        const prefData = prefResp.ok ? await prefResp.json() : {};
                        const target = prefData.useTapInterface ? 'tap_interface.html' : 'gridpage.html';
                        window.location.href = `${target}?page=home`;
                    } catch (e) {
                        window.location.href = 'gridpage.html?page=home';
                    }
                }, 1500);
                return;
            }

            alert('User profile has been generated and populated in the form. You can now review and make any adjustments before saving.');

            // Close the interview modal
            setTimeout(() => {
                this.handleCloseModal();
            }, 2000);
            
        } catch (error) {
            console.error('Error generating narrative:', error);
            this.updateStatus('Error generating user profile. Please try again.', 'error');
            alert('There was an error generating the user profile. Please try again or enter the information manually.');
        }
    }

    async generateNarrative() {
        try {
            // Prepare comprehensive interview responses for the API
            const responses = this.interviewData.responses.map(r => ({
                questionId: r.questionId,
                question: r.question,
                answer: r.answer,
                timestamp: r.timestamp || new Date().toISOString(),
                type: r.type || 'general'
            }));

            // Enhanced prompt that leverages the comprehensive nature of our questions
            const comprehensivePrompt = `Generate a detailed user profile narrative from this comprehensive interview. This information will be used by an AAC (Augmentative and Alternative Communication) system to provide personalized communication options.

Focus on creating a narrative that helps the communication system understand:
- The user's personality, preferences, and communication style
- Their relationships, interests, and daily life context  
- Their support needs and challenges
- Environmental factors that affect their communication
- Values and motivations that drive their choices

Write in third person as a cohesive, professional profile that caregivers and the AAC system can reference to provide better, more personalized communication support.`;

            // Call the backend API endpoint
            const response = await window.authenticatedFetch('/api/interview/generate-narrative', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    prompt: comprehensivePrompt,
                    responses: responses
                })
            });

            if (response.ok) {
                const data = await response.json();
                return data.narrative;
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to generate narrative');
            }
        } catch (error) {
            console.error('Error generating narrative:', error);
            
            // Fallback: Create a basic narrative from responses
            return this.createBasicNarrativeFromResponses();
        }
    }

    createBasicNarrativeFromResponses() {
        const responses = this.interviewData.responses;
        
        // Extract key information
        const nameResponse = responses.find(r => r.questionId.includes('name'));
        const userName = nameResponse ? nameResponse.answer.trim() : 'The user';
        
        let narrative = `This profile is for ${userName}.\n\n`;
        
        // Group responses by category — build dynamically so new categories aren't dropped
        const categories = {};
        responses.forEach(response => {
            const category = response.type || 'general';
            if (!categories[category]) categories[category] = [];
            categories[category].push(response);
        });
        
        // Build narrative sections
        Object.keys(categories).forEach(category => {
            const categoryResponses = categories[category];
            if (categoryResponses.length > 0) {
                const categoryTitle = category.charAt(0).toUpperCase() + category.slice(1).replace('_', ' ');
                narrative += `${categoryTitle}:\n`;
                categoryResponses.forEach(response => {
                    narrative += `${response.answer}\n`;
                });
                narrative += '\n';
            }
        });
        
        return narrative;
    }

    async populateUserInfoFields(narrative) {
        // Extract user name and birthday from responses
        const nameResponse = this.interviewData.responses.find(r => r.questionId === 'user_name');
        const birthdayResponse = this.interviewData.responses.find(r => r.questionId === 'user_birthday');

        console.log('[Interview] populateUserInfoFields: all responses:', this.interviewData.responses.map(r => ({ id: r.questionId, answer: r.answer?.substring(0, 50) })));
        console.log('[Interview] birthdayResponse:', birthdayResponse);

        // Populate the user info textarea (user_info_admin.html)
        const userInfoTextarea = document.getElementById('user-info');
        if (userInfoTextarea) {
            userInfoTextarea.value = narrative;
        }

        // Populate name DOM field if present (user_info_admin.html)
        if (nameResponse) {
            const nameField = document.getElementById('userName');
            if (nameField) nameField.value = nameResponse.answer.trim();
        }

        // Parse birthday — either from date picker (YYYY-MM-DD) or free text
        let parsedDate = null;
        if (birthdayResponse) {
            const raw = birthdayResponse.answer.trim();
            console.log('[Interview] birthday raw answer:', JSON.stringify(raw));
            if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
                parsedDate = raw;
            } else {
                parsedDate = await this.parseBirthdayFromResponse(raw);
            }
            console.log('[Interview] parsedDate:', parsedDate);
            // Populate birthday DOM field if present (user_info_admin.html)
            const birthdayField = document.getElementById('userBirthdate');
            if (birthdayField && parsedDate) {
                birthdayField.value = parsedDate;
            }
        } else {
            console.warn('[Interview] No birthday response found in interviewData.responses');
        }

        // Save name and birthday to backend so they persist regardless of which page we're on
        console.log('[Interview] window.authenticatedFetch defined:', typeof window.authenticatedFetch === 'function');
        if (typeof window.authenticatedFetch === 'function') {
            if (nameResponse) {
                try {
                    await window.authenticatedFetch('/api/user-info', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name: nameResponse.answer.trim() })
                    });
                } catch (e) {
                    console.error('Failed to save user name to backend:', e);
                }
            }
            if (parsedDate) {
                try {
                    // Load existing birthday data to preserve friendsFamily
                    let existingFriendsFamily = [];
                    const bdResp = await window.authenticatedFetch('/api/birthdays');
                    if (bdResp.ok) {
                        const bdData = await bdResp.json();
                        existingFriendsFamily = bdData.friendsFamily || [];
                    }
                    const saveResp = await window.authenticatedFetch('/api/birthdays', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ userBirthdate: parsedDate, friendsFamily: existingFriendsFamily })
                    });
                    console.log('[Interview] Birthday save response status:', saveResp.status);
                } catch (e) {
                    console.error('Failed to save birthday to backend:', e);
                }
            } else {
                console.warn('[Interview] parsedDate is null — birthday not saved to backend');
            }
        }

        // Extract and populate friends/family information
        await this.populateFriendsFamily();
    }

    async parseBirthdayFromResponse(birthdayText) {
        try {
            const prompt = `Extract a date from this text and return it in YYYY-MM-DD format. If no year is mentioned, use 2000 as default.

Text: "${birthdayText}"

Return only the date in YYYY-MM-DD format or "NONE" if no valid date can be extracted.`;
            
            const response = await this.callLLM(prompt);
            const dateMatch = response.match(/\d{4}-\d{2}-\d{2}/);
            return dateMatch ? dateMatch[0] : null;
        } catch (error) {
            console.error('Error parsing birthday:', error);
            return null;
        }
    }

    async populateFriendsFamily() {
        // Look for responses that mention family members or friends
        const familyResponses = this.interviewData.responses.filter(r => 
            r.answer.toLowerCase().includes('family') || 
            r.answer.toLowerCase().includes('friend') ||
            r.answer.toLowerCase().includes('mom') ||
            r.answer.toLowerCase().includes('dad') ||
            r.answer.toLowerCase().includes('sister') ||
            r.answer.toLowerCase().includes('brother') ||
            r.answer.toLowerCase().includes('spouse') ||
            r.answer.toLowerCase().includes('wife') ||
            r.answer.toLowerCase().includes('husband')
        );
        
        if (familyResponses.length === 0) return;
        
        const familyText = familyResponses.map(r => r.answer).join(' ');
        
        try {
            const prompt = `Extract family members and friends from this text. For each person mentioned, provide:
- Name (what the user calls them)
- Relationship (mom, dad, sister, friend, etc.)
- Brief description (1-2 sentences about them)

Text: "${familyText}"

Format as JSON array:
[{"name": "Name", "relationship": "Relationship", "about": "Brief description"}]

Return only the JSON array or empty array [] if no clear people are mentioned.`;
            
            const response = await this.callLLM(prompt);
            
            if (!response || response.trim() === '') {
                console.log('No response from LLM for family extraction');
                return;
            }
            
            try {
                // Clean the response - sometimes LLM returns extra text
                let cleanResponse = response.trim();
                
                // Find JSON array in the response
                const jsonMatch = cleanResponse.match(/\[[\s\S]*\]/);
                if (jsonMatch) {
                    cleanResponse = jsonMatch[0];
                }
                
                const people = JSON.parse(cleanResponse);
                if (Array.isArray(people) && people.length > 0) {
                    console.log('Extracted family/friends:', people);
                    // Add these to the friends/family table if the functions exist
                    if (window.addFamilyMember) {
                        people.forEach(person => {
                            if (person.name && person.relationship) {
                                window.addFamilyMember(person.name, person.relationship, person.about || '', '');
                            }
                        });
                    }
                }
            } catch (parseError) {
                console.warn('Could not parse family members JSON:', parseError);
                console.warn('Raw response was:', response);
            }
        } catch (error) {
            console.error('Error extracting family members:', error);
        }
    }

    updateStatus(message, type = 'info') {
        const statusEl = this.interviewStatus.querySelector('span');
        const iconEl = this.interviewStatus.querySelector('i');
        
        if (statusEl) {
            statusEl.textContent = message;
        }
        
        if (iconEl) {
            iconEl.className = this.getStatusIcon(type);
        }
        
        console.log(`Interview Status [${type}]: ${message}`);
    }

    getStatusIcon(type) {
        const icons = {
            info: 'fas fa-info-circle text-blue-600',
            success: 'fas fa-check-circle text-green-600',
            warning: 'fas fa-exclamation-triangle text-yellow-600',
            error: 'fas fa-times-circle text-red-600',
            listening: 'fas fa-microphone-alt text-blue-600',
            processing: 'fas fa-spinner fa-spin text-blue-600'
        };
        return icons[type] || icons.info;
    }

    updateProgress() {
        const total = this.currentQuestions.length;
        const current = Math.min(this.currentQuestionIndex + 1, total);
        this.interviewProgress.textContent = `Question ${current} of ${total}`;
    }

    addToInterviewLog(message, type) {
        if (!this.interviewLog) return;
        const logEntry = document.createElement('div');
        logEntry.className = `interview-log-entry ${type}`;
        logEntry.innerHTML = `
            <div class="flex-1">
                <div class="${this.getLogEntryClass(type)}">${message}</div>
            </div>
        `;
        this.interviewLog.appendChild(logEntry);
        this.interviewLog.classList.remove('hidden');
        this.interviewLog.scrollTop = this.interviewLog.scrollHeight;
    }

    getLogEntryClass(type) {
        const classes = {
            question: 'font-medium text-blue-800',
            answer: 'text-gray-700 italic',
            skipped: 'text-gray-500 italic'
        };
        return classes[type] || 'text-gray-700';
    }

    clearInterviewLog() {
        if (!this.interviewLog) return;
        this.interviewLog.innerHTML = '';
        this.interviewLog.classList.add('hidden');
    }

    getUserStorageKey() {
        const currentAacUserId = sessionStorage.getItem('currentAacUserId');
        if (currentAacUserId) {
            return `audioInterviewProgress_${currentAacUserId}`;
        }
        // Fallback to generic key if no user ID available
        return 'audioInterviewProgress';
    }

    async saveProgress() {
        try {
            this.interviewData.lastSaveTime = new Date().toISOString();
            
            const progressData = {
                interviewData: this.interviewData,
                currentQuestionIndex: this.currentQuestionIndex,
                currentQuestions: this.currentQuestions
            };
            
            const storageKey = this.getUserStorageKey();
            localStorage.setItem(storageKey, JSON.stringify(progressData));
            
            this.updateStatus('Progress saved', 'success');
            
            setTimeout(() => {
                if (!this.isActive) {
                    this.updateStatus('Ready to continue interview', 'info');
                }
            }, 2000);
            
        } catch (error) {
            console.error('Error saving progress:', error);
            this.updateStatus('Error saving progress', 'error');
        }
    }

    loadSavedProgress() {
        try {
            const storageKey = this.getUserStorageKey();
            let savedProgress = localStorage.getItem(storageKey);

            // If no data under the user-specific key, check the generic fallback key
            // (wizard interviews save under the generic key before the user ID is known)
            if (!savedProgress && storageKey !== 'audioInterviewProgress') {
                const genericData = localStorage.getItem('audioInterviewProgress');
                if (genericData) {
                    savedProgress = genericData;
                    localStorage.setItem(storageKey, genericData);
                    localStorage.removeItem('audioInterviewProgress');
                    console.log('Migrated interview progress from generic key to user-specific key');
                }
            }

            if (savedProgress) {
                const progressData = JSON.parse(savedProgress);

                this.interviewData = progressData.interviewData || this.interviewData;
                this.currentQuestions = progressData.currentQuestions || [...this.baseQuestions];
                // Always start review from Q1 so saved answers are visible from the beginning
                this.currentQuestionIndex = 0;
                
                // Restore interview log
                if (this.interviewData.responses.length > 0) {
                    this.clearInterviewLog();
                    this.interviewData.responses.forEach((response, index) => {
                        this.addToInterviewLog(`Q${index + 1}: ${response.question}`, 'question');
                        this.addToInterviewLog(`A${index + 1}: ${response.answer}`, 'answer');
                    });
                }
                
                console.log('Loaded saved interview progress:', this.interviewData.responses.length, 'responses');
            }
        } catch (error) {
            console.error('Error loading saved progress:', error);
        }
    }

    clearSavedProgress() {
        localStorage.removeItem(this.getUserStorageKey());
        localStorage.removeItem('audioInterviewProgress');
    }

    async _loadResponsesFromFirestore() {
        if (typeof window.authenticatedFetch !== 'function') return;
        try {
            const resp = await window.authenticatedFetch('/api/interview/responses', { method: 'GET' });
            if (!resp.ok) return;
            const data = await resp.json();
            if (Array.isArray(data.responses) && data.responses.length > 0) {
                this.interviewData.responses = data.responses;
                this.currentQuestionIndex = 0;
                this.updateProgress();
                console.log('[Interview] Loaded', data.responses.length, 'responses from Firestore');
            }
        } catch (e) {
            console.warn('[Interview] Could not load responses from Firestore:', e);
        }
    }

    async _saveResponsesToFirestore() {
        if (typeof window.authenticatedFetch !== 'function') return;
        if (this.interviewData.responses.length === 0) return;
        try {
            await window.authenticatedFetch('/api/interview/responses', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ responses: this.interviewData.responses })
            });
        } catch (e) {
            console.warn('[Interview] Could not save responses to Firestore:', e);
        }
    }

    // Method to reset interview data when user changes (called during logout/profile switch)
    resetForNewUser() {
        console.log('Resetting interview system for new user');
        
        // Clear current interview data
        this.interviewData = {
            responses: [],
            startTime: null,
            lastSaveTime: null
        };
        
        // Reset state
        this.currentQuestionIndex = 0;
        this.currentQuestions = [...this.baseQuestions];
        this.isActive = false;
        this.isPaused = false;
        
        // Clear UI
        this.clearInterviewLog();
        if (this.currentQuestion) {
            this.currentQuestion.textContent = 'Click "Start Interview" to begin gathering information about the user.';
        }
        
        // Don't automatically clear saved progress since that might be for a different user
        // Each user's progress is stored separately now
    }

}

// Initialize the interview system when the page loads
document.addEventListener('DOMContentLoaded', () => {
    // Only create if it doesn't already exist
    if (!window.audioInterviewSystem && !window.interviewSystem) {
        setTimeout(() => {
            window.audioInterviewSystem = new AudioInterviewSystem();
            console.log('Audio Interview System initialized');
        }, 1000);
    }
});

// Function to refresh interview data when user context changes
window.refreshInterviewForUser = function() {
    if (window.audioInterviewSystem) {
        console.log('Refreshing interview data for current user');
        window.audioInterviewSystem.resetForNewUser();
        window.audioInterviewSystem.loadSavedProgress();
    }
};
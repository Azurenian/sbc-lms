// Lesson Generator JavaScript Module

function lessonGenerator() {
    return {
        // Current state
        currentStep: 1,
        sessionId: null,
        websocket: null,
        
        // Form data
        selectedFile: null,
        lessonTitle: '',
        courseId: '',
        userPrompt: '',
        
        // Course data
        availableCourses: [],
        coursesLoading: false,
        coursesError: '',
        
        // UI state
        dragOver: false,
        showFoundationPrompt: false,
        showCancelModal: false,
        showProgressIndicator: false,
        isSubmitting: false,
        
        // Foundation prompt data
        foundationPromptData: {
            prompt: '',
            description: '',
            version: ''
        },
        
        // Progress tracking
        progressData: {
            stage: 'upload',
            progress: 0,
            message: 'Ready to start',
            timestamp: null
        },
        
        // Video data
        suggestedVideos: [],
        selectedVideos: [],
        videoSearchKeywords: '',
        youtubeUrl: '',
        
        // Lesson data
        generatedLessonData: null,
        lexicalEditor: null,
        
        // Initialize the lesson generator
        init() {
            console.log('Initializing Lesson Generator');
            this.loadFoundationPrompt();
            this.loadCourses();
            this.restoreSessionIfExists();
            
            // Setup beforeunload handler to warn about leaving during generation
            window.addEventListener('beforeunload', (e) => {
                if (this.currentStep === 2) {
                    e.preventDefault();
                    e.returnValue = 'Lesson generation in progress. Are you sure you want to leave?';
                }
            });
        },

        // Course loading
        async loadCourses() {
            this.coursesLoading = true;
            this.coursesError = '';
            try {
                const response = await fetch('/api/courses');
                if (response.ok) {
                    const data = await response.json();
                    if (data.courses) {
                        this.availableCourses = data.courses;
                    } else {
                        this.coursesError = 'Failed to parse courses from response.';
                    }
                } else {
                    this.coursesError = 'Failed to fetch courses from the server.';
                }
            } catch (error) {
                console.error('Error loading courses:', error);
                this.coursesError = 'An error occurred while fetching courses.';
            } finally {
                this.coursesLoading = false;
            }
        },
        
        // Computed properties
        get canStartGeneration() {
            return this.selectedFile && this.lessonTitle.trim() && this.courseId;
        },
        
        get courseDisplayText() {
            if (!this.courseId) return 'No course selected';
            const course = this.availableCourses.find(c => c.id === this.courseId);
            return course ? course.title : `Course ${this.courseId}`;
        },
        
        // Session management
        saveSessionState() {
            const state = {
                currentStep: this.currentStep,
                sessionId: this.sessionId,
                lessonTitle: this.lessonTitle,
                courseId: this.courseId,
                userPrompt: this.userPrompt,
                progressData: this.progressData,
                suggestedVideos: this.suggestedVideos,
                selectedVideos: this.selectedVideos,
                generatedLessonData: this.generatedLessonData
            };
            sessionStorage.setItem('lessonGeneratorState', JSON.stringify(state));
        },
        
        restoreSessionIfExists() {
            const savedState = sessionStorage.getItem('lessonGeneratorState');
            if (savedState) {
                try {
                    const state = JSON.parse(savedState);
                    if (state.sessionId && state.currentStep > 1) {
                        // Restore session state
                        Object.assign(this, state);
                        
                        // If we were in processing stage, reconnect to WebSocket
                        if (this.currentStep === 2 && this.sessionId) {
                            this.connectWebSocket();
                        }
                        
                        showToast('Restored previous lesson generation session', 'info');
                    }
                } catch (e) {
                    console.error('Failed to restore session:', e);
                    sessionStorage.removeItem('lessonGeneratorState');
                }
            }
        },
        
        clearSessionState() {
            sessionStorage.removeItem('lessonGeneratorState');
        },

        resetToFirstStep() {
            this.currentStep = 1;
            this.sessionId = null;
            this.progressData = { stage: 'upload', progress: 0, message: 'Ready to start', timestamp: null };
            this.disconnectWebSocket();
            this.clearSessionState();
            this.notifyGlobalIndicator(false); // Hide indicator
        },

        notifyGlobalIndicator(show = true) {
            const event = new CustomEvent('global-progress-update', {
                detail: {
                    show: show && this.currentStep === 2,
                    sessionId: this.sessionId,
                    progressData: this.progressData
                }
            });
            window.dispatchEvent(event);
        },
        
        // Foundation prompt loading
        async loadFoundationPrompt() {
            try {
                console.log('Loading foundation prompt...');
                const response = await fetch('http://localhost:8000/foundation-prompt');
                if (response.ok) {
                    const data = await response.json();
                    console.log('Foundation prompt data received:', data);
                    this.foundationPromptData = {
                        prompt: data.foundation_prompt || 'No prompt available',
                        description: data.description || 'No description available',
                        version: data.version || '1.0'
                    };
                    console.log('Foundation prompt data set:', this.foundationPromptData);
                } else {
                    console.error('Failed to load foundation prompt, status:', response.status);
                    // Set fallback data
                    this.foundationPromptData = {
                        prompt: 'Foundation prompt unavailable - please check pi-ai server connection',
                        description: 'Error loading foundation prompt',
                        version: 'Error'
                    };
                }
            } catch (error) {
                console.error('Error loading foundation prompt:', error);
                // Set fallback data
                this.foundationPromptData = {
                    prompt: 'Foundation prompt unavailable - please check pi-ai server connection',
                    description: 'Error loading foundation prompt',
                    version: 'Error'
                };
            }
        },
        
        // File handling
        handleFileSelect(event) {
            const file = event.target.files[0];
            this.setSelectedFile(file);
        },
        
        handleFileDrop(event) {
            this.dragOver = false;
            const file = event.dataTransfer.files[0];
            if (file && file.type === 'application/pdf') {
                this.setSelectedFile(file);
                // Update file input
                const fileInput = document.getElementById('pdfFile');
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                fileInput.files = dataTransfer.files;
            } else {
                showToast('Please select a valid PDF file', 'error');
            }
        },
        
        setSelectedFile(file) {
            if (file && file.type === 'application/pdf') {
                if (file.size > 10 * 1024 * 1024) { // 10MB limit
                    showToast('File size must be less than 10MB', 'error');
                    return;
                }
                this.selectedFile = file;
                showToast(`Selected: ${file.name}`, 'success');
            } else {
                showToast('Please select a valid PDF file', 'error');
            }
        },
        
        // Lesson generation process
        async startGeneration() {
            if (!this.canStartGeneration) {
                showToast('Please fill in all required fields', 'error');
                return;
            }
            
            try {
                const tokenResponse = await fetch('/api/token');
                if (!tokenResponse.ok) throw new Error('Authentication failed');
                const tokenData = await tokenResponse.json();
                
                const formData = new FormData();
                formData.append('file', this.selectedFile);
                formData.append('title', this.lessonTitle);
                formData.append('course_id', this.courseId);
                formData.append('auth_token', tokenData.token);
                const combinedPrompt = `${this.foundationPromptData.prompt}\n${this.userPrompt}`;
formData.append('prompt', combinedPrompt);
                
                this.currentStep = 2;
                this.progressData = {
                    stage: 'upload',
                    progress: 0,
                    message: 'Starting lesson generation...',
                    timestamp: new Date().toISOString()
                };
                showToast('Starting AI lesson generation...', 'info');
                
                const response = await fetch('http://localhost:8000/process-pdf/', {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    const result = await response.json();
                    this.sessionId = result.session_id;
                    this.saveSessionState(); // Save session ID immediately
                    this.connectWebSocket(); // Connect AFTER getting session ID
                    this.notifyGlobalIndicator();
                } else {
                    const error = await response.json();
                    throw new Error(error.detail || 'Failed to start generation');
                }
                
            } catch (error) {
                console.error('Generation start error:', error);
                showToast(`Error: ${error.message}`, 'error');
                this.resetToFirstStep();
            }
        },

        async fetchLessonResult() {
            if (!this.sessionId) return;
            console.log('Fetching final lesson result...');
            try {
                const response = await fetch(`http://localhost:8000/lesson-result/${this.sessionId}`);
                if (response.ok) {
                    const result = await response.json();
                    this.generatedLessonData = result.lesson_data;
                    this.suggestedVideos = result.youtube_videos || [];
                    
                    this.currentStep = 3;
                    this.saveSessionState();
                    this.disconnectWebSocket();
                    
                    showToast('Lesson generation completed! Please select videos.', 'success');
                } else {
                    const error = await response.json();
                    throw new Error(error.detail || 'Failed to fetch lesson result.');
                }
            } catch (error) {
                console.error('Failed to fetch lesson result:', error);
                showToast(`Error: ${error.message}`, 'error');
                this.resetToFirstStep();
            }
        },
        
        // WebSocket connection for progress updates
        connectWebSocket() {
            if (!this.sessionId) return;
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                console.log("WebSocket already connected.");
                return;
            }
            
            try {
                const wsUrl = `ws://localhost:8000/ws/lesson-progress/${this.sessionId}`;
                this.websocket = new WebSocket(wsUrl);
                
                this.websocket.onopen = () => {
                    console.log('WebSocket connected for session:', this.sessionId);
                };
                
                this.websocket.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        this.progressData = data;
                        this.saveSessionState();
                        this.notifyGlobalIndicator(true); // Notify on every update
                        
                        if (data.stage === 'error') {
                            showToast(`Generation failed: ${data.message}`, 'error');
                            this.resetToFirstStep();
                            return;
                        }
                        
                        // Check if generation is complete
                        if (data.stage === 'selection' && data.progress >= 100) {
                            this.fetchLessonResult();
                        }
                    } catch (e) {
                        console.error('Error parsing WebSocket message:', e);
                    }
                };
                
                this.websocket.onclose = () => {
                    console.log('WebSocket disconnected');
                    this.websocket = null;
                };
                
                this.websocket.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    showToast('WebSocket connection error. Please refresh.', 'error');
                };
                
            } catch (error) {
                console.error('Failed to connect WebSocket:', error);
            }
        },
        
        disconnectWebSocket() {
            if (this.websocket) {
                this.websocket.close();
            }
        },
        
        // Progress helpers
        getStageIcon(stage) {
            const icons = {
                upload: '📤',
                processing: '🧠',
                youtube: '🎥',
                selection: '✅',
                cancelled: '⛔'
            };
            return icons[stage] || '⏳';
        },
        
        getStageName(stage) {
            const names = {
                upload: 'File Upload',
                processing: 'AI Analysis',
                youtube: 'Media Generation', 
                selection: 'Ready for Selection',
                cancelled: 'Cancelled'
            };
            return names[stage] || 'Processing';
        },
        
        isStageCompleted(stage) {
            const stages = ['upload', 'processing', 'youtube', 'selection'];
            const currentIndex = stages.indexOf(this.progressData.stage);
            const checkIndex = stages.indexOf(stage);
            return currentIndex > checkIndex || (currentIndex === checkIndex && this.progressData.progress >= 100);
        },
        
        // Video selection
        isVideoSelected(video) {
            return this.selectedVideos.some(v => v.videoId === video.videoId);
        },
        
        toggleVideoSelection(video) {
            if (this.isVideoSelected(video)) {
                this.removeVideoSelection(video);
            } else {
                this.selectedVideos.push(video);
                showToast(`Added: ${video.title}`, 'success');
            }
        },
        
        removeVideoSelection(video) {
            this.selectedVideos = this.selectedVideos.filter(v => v.videoId !== video.videoId);
            showToast(`Removed: ${video.title}`, 'info');
        },
        
        async searchMoreVideos() {
            if (!this.videoSearchKeywords.trim()) {
                showToast('Please enter search keywords', 'error');
                return;
            }
            
            try {
                const response = await fetch('http://localhost:8000/search-youtube/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        keywords: this.videoSearchKeywords.split(' ').filter(k => k.trim())
                    })
                });
                
                if (response.ok) {
                    const result = await response.json();
                    // Add new videos to suggested videos (avoid duplicates)
                    const newVideos = result.videos.filter(newVideo => 
                        !this.suggestedVideos.some(existing => existing.videoId === newVideo.videoId)
                    );
                    this.suggestedVideos.push(...newVideos);
                    showToast(`Found ${newVideos.length} new videos`, 'success');
                } else {
                    throw new Error('Search failed');
                }
            } catch (error) {
                console.error('Video search error:', error);
                showToast('Failed to search videos', 'error');
            }
        },
        
        async addYoutubeVideo() {
            if (!this.youtubeUrl.trim()) {
                showToast('Please enter a YouTube URL', 'error');
                return;
            }
            
            try {
                const response = await fetch('http://localhost:8000/add-youtube-video/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        link: this.youtubeUrl
                    })
                });
                
                if (response.ok) {
                    const result = await response.json();
                    // Check if video already exists
                    if (!this.suggestedVideos.some(v => v.videoId === result.video.videoId)) {
                        this.suggestedVideos.push(result.video);
                        showToast(`Added video: ${result.video.title}`, 'success');
                        this.youtubeUrl = '';
                    } else {
                        showToast('Video already in list', 'warning');
                    }
                } else {
                    const error = await response.json();
                    throw new Error(error.detail || 'Failed to add video');
                }
            } catch (error) {
                console.error('Add video error:', error);
                showToast(`Failed to add video: ${error.message}`, 'error');
            }
        },
        
        proceedToPreview() {
            if (this.selectedVideos.length === 0) {
                showToast('Please select at least one video', 'error');
                return;
            }
            this.currentStep = 4;
            this.saveSessionState();
            
            // Initialize Lexical editor with a delay to ensure DOM is ready
            setTimeout(() => {
                this.initializeLexicalEditor();
            }, 100);
            
            showToast('Moved to lesson preview', 'info');
        },
        
        // Lesson preview and editing
        initializeLexicalEditor() {
            if (window.LessonLexicalEditor && this.generatedLessonData) {
                try {
                    this.lexicalEditor = new window.LessonLexicalEditor('lexical-editor');
                    this.lexicalEditor.loadLessonData(this.generatedLessonData);
                    console.log('Lexical editor initialized successfully');
                } catch (error) {
                    console.error('Failed to initialize Lexical editor:', error);
                    showToast('Editor initialization failed, using fallback preview', 'warning');
                }
            } else {
                console.warn('LessonLexicalEditor not available or no lesson data');
            }
        },
        
        getPreviewContent() {
            if (!this.generatedLessonData) return '<p>No lesson data available</p>';
            
            // Simple preview of generated content
            // This is used as fallback when Lexical editor is not available
            return `
                <div class="lesson-preview">
                    <h3>${this.lessonTitle}</h3>
                    <p><strong>Course ID:</strong> ${this.courseId}</p>
                    <p><strong>Content Structure:</strong> ${this.generatedLessonData.content?.root?.children?.length || 0} sections</p>
                    <p><strong>Audio:</strong> Generated narration included</p>
                    <p><strong>Videos:</strong> ${this.selectedVideos.length} videos selected</p>
                    <div class="content-preview">
                        <p><em>Lexical editor will render the full lesson content above...</em></p>
                    </div>
                </div>
            `;
        },
        
        resetToOriginal() {
            if (this.lexicalEditor) {
                this.lexicalEditor.reset();
                showToast('Reset to original AI-generated content', 'success');
            } else {
                showToast('Editor not available for reset', 'warning');
            }
        },
        
        async submitLesson() {
            if (this.isSubmitting) return;
            
            this.isSubmitting = true;
            
            try {
                // Get auth token
                const tokenResponse = await fetch('/api/token');
                if (!tokenResponse.ok) {
                    throw new Error('Authentication failed');
                }
                const tokenData = await tokenResponse.json();
                
                // Get potentially modified lesson data from Lexical editor
                let finalLessonData = this.generatedLessonData;
                if (this.lexicalEditor) {
                    finalLessonData = this.lexicalEditor.getLessonData();
                    if (this.lexicalEditor.isModified()) {
                        showToast('Submitting lesson with your modifications...', 'info');
                    }
                }
                
                // Prepare final lesson data
                const submitData = {
                    selected_videos: this.selectedVideos,
                    lesson_data: finalLessonData,
                    auth_token: tokenData.token
                };
                
                // Submit to pi-ai
                const response = await fetch('http://localhost:8000/finish/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(submitData)
                });
                
                if (response.ok) {
                    const result = await response.json();
                    
                    // Cleanup temporary files
                    await fetch('http://localhost:8000/cleanup/', { method: 'POST' });
                    
                    // Clear session state
                    this.clearSessionState();
                    
                    showToast('Lesson submitted successfully!', 'success');
                    
                    // Try to get lesson URL from payload result
                    const lessonId = result.payload_result?.doc?.id || result.payload_result?.id;
                    if (lessonId) {
                        showToast(`Redirecting to lesson... (ID: ${lessonId})`, 'info');
                        setTimeout(() => {
                            // In a real implementation, this would redirect to the actual lesson page
                            // For now, redirect to dashboard with lesson info
                            window.location.href = `/dashboard?lesson_created=${lessonId}`;
                        }, 2000);
                    } else {
                        setTimeout(() => {
                            window.location.href = '/dashboard';
                        }, 2000);
                    }
                    
                } else {
                    const error = await response.json();
                    throw new Error(error.detail || 'Submission failed');
                }
                
            } catch (error) {
                console.error('Submission error:', error);
                showToast(`Submission failed: ${error.message}`, 'error');
            } finally {
                this.isSubmitting = false;
            }
        },
        
        // Cancellation
        async cancelGeneration() {
            this.showCancelModal = false;
            
            try {
                if (this.sessionId) {
                    await fetch(`http://localhost:8000/cancel-lesson-generation/${this.sessionId}`, {
                        method: 'POST'
                    });
                }
                
                this.disconnectWebSocket();
                this.clearSessionState();
                
                // Reset to initial state
                this.currentStep = 1;
                this.sessionId = null;
                this.progressData = {
                    stage: 'upload',
                    progress: 0,
                    message: 'Ready to start',
                    timestamp: null
                };
                
                showToast('Lesson generation cancelled', 'info');
                
            } catch (error) {
                console.error('Cancellation error:', error);
                showToast('Failed to cancel properly, but generation stopped', 'warning');
            }
        },
        
        // Persistent progress indicator integration
        returnToGeneration() {
            // This would be called when clicking the progress indicator
            this.showProgressIndicator = false;
            // The global indicator handles navigation
        },
        
        // Notify global progress indicator
        notifyGlobalIndicator() {
            // Get global indicator instance
            const globalIndicator = document.getElementById('global-progress-indicator')?.__x?.$data;
            if (globalIndicator && this.currentStep === 2 && this.sessionId) {
                globalIndicator.sessionId = this.sessionId;
                globalIndicator.progressData = this.progressData;
                globalIndicator.showIndicator = true;
                globalIndicator.connectWebSocket();
            }
        },

        // Course selection helper
        getCourseDisplayName(courseId) {
            const course = this.availableCourses.find(c => c.id === courseId);
            return course ? course.title : `Course ${courseId}`;
        },

        // Validation helper
        validateForm() {
            const errors = [];
            
            if (!this.selectedFile) {
                errors.push('Please select a PDF file');
            }
            
            if (!this.lessonTitle.trim()) {
                errors.push('Please enter a lesson title');
            }
            
            if (!this.courseId) {
                errors.push('Please select a course');
            }
            
            return errors;
        }
    };
}

// Global helper functions
function showToast(message, type = 'info') {
    // Use the existing toast function from the main application
    if (window.showToast) {
        window.showToast(message, type);
    } else {
        console.log(`[${type.toUpperCase()}] ${message}`);
    }
}
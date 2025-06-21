// Basic Lexical Editor Integration for Lesson Preview
// This is a simplified version that renders and allows basic editing of Lexical JSON

class LessonLexicalEditor {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.data = null;
        this.originalData = null;
        this.init();
    }
    
    init() {
        if (!this.container) {
            console.error('Lexical editor container not found');
            return;
        }
        
        this.container.innerHTML = `
            <div class="lexical-toolbar">
                <div class="toolbar-group">
                    <button type="button" class="toolbar-btn" data-command="bold" title="Bold">
                        <strong>B</strong>
                    </button>
                    <button type="button" class="toolbar-btn" data-command="italic" title="Italic">
                        <em>I</em>
                    </button>
                    <button type="button" class="toolbar-btn" data-command="underline" title="Underline">
                        <u>U</u>
                    </button>
                </div>
                <div class="toolbar-group">
                    <select class="toolbar-select" data-command="formatBlock" title="Text Format">
                        <option value="p">Paragraph</option>
                        <option value="h1">Heading 1</option>
                        <option value="h2">Heading 2</option>
                        <option value="h3">Heading 3</option>
                    </select>
                </div>
                <div class="toolbar-group">
                    <button type="button" class="toolbar-btn" data-command="insertUnorderedList" title="Bullet List">
                        • List
                    </button>
                    <button type="button" class="toolbar-btn" data-command="insertOrderedList" title="Numbered List">
                        1. List
                    </button>
                </div>
                <div class="toolbar-group">
                    <button type="button" class="toolbar-btn" data-command="undo" title="Undo">
                        ↶ Undo
                    </button>
                    <button type="button" class="toolbar-btn" data-command="redo" title="Redo">
                        ↷ Redo
                    </button>
                </div>
            </div>
            <div class="lexical-editor-content" contenteditable="true">
                <p class="placeholder-text">Lesson content will appear here...</p>
            </div>
        `;
        
        this.toolbar = this.container.querySelector('.lexical-toolbar');
        this.contentArea = this.container.querySelector('.lexical-editor-content');
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // Basic content change detection
        this.contentArea.addEventListener('input', () => {
            this.markAsModified();
            this.updateToolbarState();
        });
        
        // Selection change to update toolbar state
        this.contentArea.addEventListener('selectionchange', () => {
            this.updateToolbarState();
        });
        
        // Toolbar button clicks
        this.toolbar.addEventListener('click', (e) => {
            if (e.target.classList.contains('toolbar-btn')) {
                e.preventDefault();
                const command = e.target.getAttribute('data-command');
                this.executeCommand(command);
            }
        });
        
        // Toolbar select changes
        this.toolbar.addEventListener('change', (e) => {
            if (e.target.classList.contains('toolbar-select')) {
                e.preventDefault();
                const command = e.target.getAttribute('data-command');
                const value = e.target.value;
                this.executeCommand(command, value);
            }
        });
        
        // Focus handling
        this.contentArea.addEventListener('focus', () => {
            this.updateToolbarState();
        });
        
        // Prevent default drag/drop to avoid issues
        this.contentArea.addEventListener('dragover', (e) => e.preventDefault());
        this.contentArea.addEventListener('drop', (e) => e.preventDefault());
        
        // Keyboard shortcuts
        this.contentArea.addEventListener('keydown', (e) => {
            this.handleKeyboardShortcuts(e);
        });
    }
    
    executeCommand(command, value = null) {
        // Focus the content area first
        this.contentArea.focus();
        
        try {
            if (value) {
                document.execCommand(command, false, value);
            } else {
                document.execCommand(command, false);
            }
            this.markAsModified();
            this.updateToolbarState();
        } catch (error) {
            console.warn('Command execution failed:', command, error);
        }
    }
    
    updateToolbarState() {
        // Update button states based on current selection
        const selection = window.getSelection();
        if (selection.rangeCount === 0) return;
        
        // Update bold button
        const boldBtn = this.toolbar.querySelector('[data-command="bold"]');
        if (boldBtn) {
            boldBtn.classList.toggle('active', document.queryCommandState('bold'));
        }
        
        // Update italic button
        const italicBtn = this.toolbar.querySelector('[data-command="italic"]');
        if (italicBtn) {
            italicBtn.classList.toggle('active', document.queryCommandState('italic'));
        }
        
        // Update underline button
        const underlineBtn = this.toolbar.querySelector('[data-command="underline"]');
        if (underlineBtn) {
            underlineBtn.classList.toggle('active', document.queryCommandState('underline'));
        }
        
        // Update format select
        const formatSelect = this.toolbar.querySelector('[data-command="formatBlock"]');
        if (formatSelect) {
            const formatValue = document.queryCommandValue('formatBlock').toLowerCase();
            formatSelect.value = formatValue || 'p';
        }
    }
    
    handleKeyboardShortcuts(e) {
        // Handle common keyboard shortcuts
        if (e.ctrlKey || e.metaKey) {
            switch (e.key) {
                case 'b':
                    e.preventDefault();
                    this.executeCommand('bold');
                    break;
                case 'i':
                    e.preventDefault();
                    this.executeCommand('italic');
                    break;
                case 'u':
                    e.preventDefault();
                    this.executeCommand('underline');
                    break;
                case 'z':
                    if (e.shiftKey) {
                        e.preventDefault();
                        this.executeCommand('redo');
                    } else {
                        e.preventDefault();
                        this.executeCommand('undo');
                    }
                    break;
            }
        }
    }
    
    loadLessonData(lessonData) {
        this.originalData = JSON.parse(JSON.stringify(lessonData));
        this.data = lessonData;
        this.renderContent();
    }
    
    renderContent() {
        if (!this.data || !this.data.content || !this.data.content.root) {
            this.contentArea.innerHTML = '<p class="placeholder-text">No lesson content available</p>';
            return;
        }
        
        const children = this.data.content.root.children || [];
        const html = this.renderChildren(children);
        this.contentArea.innerHTML = html || '<p class="placeholder-text">Empty lesson content</p>';
    }
    
    renderChildren(children) {
        return children.map(node => this.renderNode(node)).join('');
    }
    
    renderNode(node) {
        switch (node.type) {
            case 'paragraph':
                return `<p>${this.renderChildren(node.children || [])}</p>`;
            
            case 'heading':
                const tag = node.tag || 'h2';
                return `<${tag}>${this.renderChildren(node.children || [])}</${tag}>`;
            
            case 'text':
                let text = this.escapeHtml(node.text || '');
                
                // Apply formatting
                if (node.format) {
                    if (node.format & 1) text = `<strong>${text}</strong>`; // Bold
                    if (node.format & 2) text = `<em>${text}</em>`; // Italic
                    if (node.format & 4) text = `<u>${text}</u>`; // Underline
                }
                
                return text;
            
            case 'list':
                const listTag = node.listType === 'number' ? 'ol' : 'ul';
                return `<${listTag}>${this.renderChildren(node.children || [])}</${listTag}>`;
            
            case 'listitem':
                return `<li>${this.renderChildren(node.children || [])}</li>`;
            
            case 'upload':
                // Handle media uploads (audio/video)
                if (node.relationTo === 'media') {
                    return this.renderMediaNode(node);
                }
                return '';
            
            case 'upload-local-audio':
                // Handle local audio files
                return '<div class="media-placeholder">🎵 Audio narration will be embedded here</div>';
            
            default:
                console.warn('Unknown node type:', node.type);
                return '';
        }
    }
    
    renderMediaNode(node) {
        // Debug logging to see what we're working with
        console.log('Rendering media node:', node);
        
        // Extract meaningful identifiers
        let nodeId = node.id || 'unknown';
        let mediaId = 'unknown';
        let displayValue = 'Unknown Media';
        
        if (node.value && typeof node.value === 'object') {
            mediaId = node.value.id || 'unknown';
            displayValue = node.value.filename || node.value.alt || `Media ID: ${mediaId}`;
        } else if (node.value && typeof node.value === 'string') {
            displayValue = node.value;
        }
        
        // Store the original node as JSON to preserve it completely
        const originalNodeData = JSON.stringify(node);
        
        return `<div class="media-placeholder"
                     data-original-node='${originalNodeData.replace(/'/g, '&apos;')}'
                     data-media-id="${mediaId}"
                     data-node-id="${nodeId}">
            🎬 Media content: ${displayValue}
        </div>`;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    markAsModified() {
        this.container.classList.add('modified');
    }
    
    isModified() {
        return this.container.classList.contains('modified');
    }
    
    // Convert HTML back to Lexical JSON
    getLessonData() {
        if (!this.isModified()) {
            return this.data;
        }
        
        // Parse the current HTML content back to Lexical JSON
        const modifiedData = JSON.parse(JSON.stringify(this.data));
        const htmlContent = this.contentArea.innerHTML;
        
        // Convert HTML to Lexical nodes
        const parser = new DOMParser();
        const doc = parser.parseFromString(`<div>${htmlContent}</div>`, 'text/html');
        const containerElement = doc.body.firstChild;
        
        // Convert the HTML structure back to Lexical JSON
        const newChildren = this.htmlToLexical(containerElement);
        
        // Update the content structure
        modifiedData.content.root.children = newChildren;
        modifiedData._isModified = true;
        
        return modifiedData;
    }
    
    htmlToLexical(element) {
        const children = [];
        let pendingTextNodes = [];
        
        // Helper function to wrap pending text nodes in a paragraph
        const wrapPendingText = () => {
            if (pendingTextNodes.length > 0) {
                children.push({
                    type: 'paragraph',
                    children: [...pendingTextNodes],
                    direction: 'ltr',
                    format: '',
                    indent: 0,
                    version: 1,
                    textFormat: 0,
                    textStyle: ''
                });
                pendingTextNodes = [];
            }
        };
        
        for (const child of element.childNodes) {
            if (child.nodeType === Node.TEXT_NODE) {
                const text = child.textContent.trim();
                if (text) {
                    pendingTextNodes.push({
                        type: 'text',
                        text: text,
                        format: 0,
                        style: '',
                        mode: 'normal',
                        detail: 0
                    });
                }
            } else if (child.nodeType === Node.ELEMENT_NODE) {
                // Wrap any pending text nodes before adding block elements
                wrapPendingText();
                
                const lexicalNode = this.elementToLexical(child);
                if (lexicalNode) {
                    if (Array.isArray(lexicalNode)) {
                        children.push(...lexicalNode);
                    } else {
                        children.push(lexicalNode);
                    }
                }
            }
        }
        
        // Wrap any remaining text nodes
        wrapPendingText();
        
        return children;
    }
    
    elementToLexical(element) {
        const tagName = element.tagName.toLowerCase();
        
        switch (tagName) {
            case 'p':
                return {
                    type: 'paragraph',
                    children: this.htmlToLexical(element),
                    direction: 'ltr',
                    format: '',
                    indent: 0,
                    version: 1
                };
                
            case 'h1':
            case 'h2':
            case 'h3':
            case 'h4':
            case 'h5':
            case 'h6':
                return {
                    type: 'heading',
                    tag: tagName,
                    children: this.htmlToLexical(element),
                    direction: 'ltr',
                    format: '',
                    indent: 0,
                    version: 1
                };
                
            case 'ul':
                return {
                    type: 'list',
                    listType: 'bullet',
                    start: 1,
                    tag: 'ul',
                    children: this.htmlToLexical(element),
                    direction: 'ltr',
                    format: '',
                    indent: 0,
                    version: 1
                };
                
            case 'ol':
                return {
                    type: 'list',
                    listType: 'number',
                    start: 1,
                    tag: 'ol',
                    children: this.htmlToLexical(element),
                    direction: 'ltr',
                    format: '',
                    indent: 0,
                    version: 1
                };
                
            case 'li':
                return {
                    type: 'listitem',
                    value: 1,
                    children: this.htmlToLexical(element),
                    direction: 'ltr',
                    format: '',
                    indent: 0,
                    version: 1
                };
                
            case 'strong':
            case 'b':
                // Handle bold formatting inline
                return this.processInlineFormatting(element, 1); // Bold flag
                
            case 'em':
            case 'i':
                // Handle italic formatting inline
                return this.processInlineFormatting(element, 2); // Italic flag
                
            case 'u':
                // Handle underline formatting inline
                return this.processInlineFormatting(element, 4); // Underline flag
                
            case 'div':
                // Handle media placeholders - skip them entirely to avoid corruption
                if (element.classList.contains('media-placeholder')) {
                    console.log('Skipping media placeholder to avoid corruption');
                    return null;
                }
                // For other divs, just process children
                return this.htmlToLexical(element);
                
            case 'br':
                return {
                    type: 'linebreak',
                    version: 1
                };
                
            default:
                // For unknown elements, just process their children
                return this.htmlToLexical(element);
        }
    }
    
    processInlineFormatting(element, formatFlag) {
        // Process inline formatting elements without creating standalone text nodes
        const textContent = element.textContent.trim();
        if (textContent) {
            return [{
                type: 'text',
                text: textContent,
                format: formatFlag,
                style: '',
                mode: 'normal',
                detail: 0
            }];
        }
        return [];
    }
    
    findOriginalMediaNode(nodeId) {
        // Search through the original lesson data to find the media node by ID
        if (!this.originalData || !this.originalData.content || !this.originalData.content.root) {
            return null;
        }
        
        const searchInChildren = (children) => {
            for (const child of children) {
                if (child.type === 'upload' && child.id === nodeId) {
                    return child;
                }
                if (child.children) {
                    const found = searchInChildren(child.children);
                    if (found) return found;
                }
            }
            return null;
        };
        
        return searchInChildren(this.originalData.content.root.children || []);
    }

    reset() {
        this.data = JSON.parse(JSON.stringify(this.originalData));
        this.renderContent();
        this.container.classList.remove('modified');
    }
    
    // Get a summary of the lesson content
    getSummary() {
        if (!this.data || !this.data.content || !this.data.content.root) {
            return { sections: 0, hasAudio: false, hasVideo: false };
        }
        
        const children = this.data.content.root.children || [];
        let sections = 0;
        let hasAudio = false;
        let hasVideo = false;
        
        children.forEach(node => {
            if (node.type === 'heading') {
                sections++;
            } else if (node.type === 'upload' || node.type === 'upload-local-audio') {
                if (node.relationTo === 'media' || node.type === 'upload-local-audio') {
                    hasAudio = true;
                }
            }
        });
        
        return { sections, hasAudio, hasVideo };
    }
}

// Global function to initialize the editor
function initializeLessonEditor(containerId = 'lexical-editor') {
    return new LessonLexicalEditor(containerId);
}

// Export for use in lesson generator
window.LessonLexicalEditor = LessonLexicalEditor;
window.initializeLessonEditor = initializeLessonEditor;
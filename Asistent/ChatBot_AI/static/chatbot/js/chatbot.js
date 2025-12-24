/**
 * ChatBot AI - Client Side
 * Real API integration
 */

(function () {
    const widget = document.getElementById('chatbotWidget');
    if (!widget) return;

    const STORAGE_KEY = 'idealimage_chatbot_state_v1';

    // Elements
    const toggleBtn = widget.querySelector('#chatbotToggle');
    const closeBtn = widget.querySelector('#chatbotClose');
    const windowEl = widget.querySelector('#chatbotWindow');
    const badge = widget.querySelector('#chatbotBadge');
    const messagesEl = widget.querySelector('#chatbotMessages');
    const typingEl = widget.querySelector('#chatbotTyping');
    const inputEl = widget.querySelector('#chatbotInput');
    const sendBtn = widget.querySelector('#chatbotSend');
    const welcomeMessage = widget.querySelector('#welcomeMessage');
    const welcomeTime = widget.querySelector('#welcomeTime');
    const contactBtn = widget.querySelector('#showContactForm');
    const contactWrapper = widget.querySelector('#contactAdminForm');
    const contactCloseBtn = widget.querySelector('#closeContactForm');
    const contactSubmitBtn = widget.querySelector('#sendContactForm');
    const contactName = widget.querySelector('#contactName');
    const contactEmail = widget.querySelector('#contactEmail');
    const contactMessage = widget.querySelector('#contactMessage');

    // State
    const loadState = () => {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            return raw ? JSON.parse(raw) : { isOpen: false };
        } catch {
            return { isOpen: false };
        }
    };

    const saveState = (state) => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    };

    const state = loadState();

    // Get CSRF token
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Update welcome time
    const updateWelcomeTime = () => {
        if (!welcomeTime) return;
        const now = new Date();
        welcomeTime.textContent = now.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
    };

    // Toggle window
    const toggleWindow = (forceValue) => {
        const shouldOpen = typeof forceValue === 'boolean' ? forceValue : windowEl.style.display === 'none';
        windowEl.style.display = shouldOpen ? 'flex' : 'none';
        badge.style.display = shouldOpen ? 'none' : badge.style.display;
        state.isOpen = shouldOpen;
        saveState(state);
        if (shouldOpen) {
            updateWelcomeTime();
            inputEl.focus();
        }
    };

    // Auto resize textarea
    const autoResize = () => {
        inputEl.style.height = 'auto';
        inputEl.style.height = `${Math.min(inputEl.scrollHeight, 120)}px`;
    };

    // Scroll to bottom
    const scrollToBottom = () => {
        messagesEl.scrollTo({ top: messagesEl.scrollHeight, behavior: 'smooth' });
    };

    // Create message element
    const createMessage = (content, type = 'bot', useHTML = false) => {
        const wrapper = document.createElement('div');
        wrapper.className = `chatbot-message chatbot-message-${type}`;
        const avatar = document.createElement('div');
        avatar.className = 'chatbot-message-avatar';
        avatar.textContent = type === 'bot' ? '🤖' : '🙂';
        const body = document.createElement('div');
        body.className = 'chatbot-message-content';
        const bubble = document.createElement('div');
        bubble.className = 'chatbot-message-text';
        
        // Use innerHTML for FAQ responses with HTML
        if (useHTML) {
            bubble.innerHTML = content;
        } else {
            bubble.textContent = content;
        }
        
        const timeEl = document.createElement('div');
        timeEl.className = 'chatbot-message-time';
        timeEl.textContent = new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
        body.appendChild(bubble);
        body.appendChild(timeEl);
        wrapper.appendChild(avatar);
        wrapper.appendChild(body);
        return wrapper;
    };

    // Send message to API
    const sendMessage = async (userText) => {
        if (!userText || !userText.trim()) return;
        
        // Add user message to UI
        messagesEl.appendChild(createMessage(userText, 'user'));
        scrollToBottom();
        
        // Show typing indicator
        typingEl.style.display = 'flex';
        scrollToBottom();
        
        try {
            const apiUrl = window.CHATBOT_API?.message || '/asistent/api/chatbot/message/';
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ message: userText })
            });
            
            const data = await response.json();
            typingEl.style.display = 'none';
            
            if (data.success) {
                // Add bot response (use innerHTML for HTML content from AI, FAQ, articles)
                const useHTML = data.source === 'ai' || data.source === 'faq' || data.source === 'article_search';
                const botMessage = createMessage(data.response, 'bot', useHTML);
                messagesEl.appendChild(botMessage);
                
                // Show contact form button if needed
                if (data.show_contact_form && contactBtn && contactBtn.parentElement) {
                    contactBtn.parentElement.style.display = 'block';
                }
            } else {
                // Error response
                messagesEl.appendChild(createMessage(data.error || 'Произошла ошибка', 'bot'));
                if (data.show_contact_form && contactBtn && contactBtn.parentElement) {
                    contactBtn.parentElement.style.display = 'block';
                }
            }
        } catch (error) {
            typingEl.style.display = 'none';
            messagesEl.appendChild(createMessage('Ошибка соединения. Попробуйте позже.', 'bot'));
            console.error('Chatbot error:', error);
        }
        
        scrollToBottom();
    };

    // Handle send
    const handleSend = () => {
        const value = inputEl.value.trim();
        if (!value) return;
        
        sendMessage(value);
        inputEl.value = '';
        autoResize();
    };

    // Send contact form
    const sendContactForm = async () => {
        const name = contactName.value.trim();
        const email = contactEmail.value.trim();
        const message = contactMessage.value.trim();
        
        if (!name || !email || !message) {
            alert('Пожалуйста, заполните все обязательные поля.');
            return;
        }
        
        try {
            const apiUrl = window.CHATBOT_API?.contact || '/asistent/api/chatbot/contact-admin/';
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ name, email, message })
            });
            
            const data = await response.json();
            
            if (data.success) {
                messagesEl.appendChild(createMessage(data.message, 'bot'));
                scrollToBottom();
                contactWrapper.style.display = 'none';
                contactBtn.parentElement.style.display = 'block';
                contactName.value = '';
                contactEmail.value = '';
                contactMessage.value = '';
            } else {
                alert(data.error || 'Ошибка отправки сообщения');
            }
        } catch (error) {
            alert('Ошибка соединения. Попробуйте позже.');
            console.error('Contact form error:', error);
        }
    };

    // Load settings from API
    const loadSettings = async () => {
        try {
            const apiUrl = window.CHATBOT_API?.settings || '/asistent/api/chatbot/settings/';
            const response = await fetch(apiUrl);
            const data = await response.json();
            
            if (data.welcome_message && welcomeMessage) {
                welcomeMessage.textContent = data.welcome_message;
            }
        } catch (error) {
            console.error('Failed to load chatbot settings:', error);
        }
    };

    // Event listeners
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => toggleWindow());
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', () => toggleWindow(false));
    }

    if (sendBtn) {
        sendBtn.addEventListener('click', (event) => {
            event.preventDefault();
            handleSend();
        });
    }

    if (inputEl) {
        inputEl.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                handleSend();
            }
        });
        inputEl.addEventListener('input', autoResize);
    }

    if (contactBtn && contactWrapper) {
        contactBtn.addEventListener('click', () => {
            contactWrapper.style.display = 'block';
            contactBtn.parentElement.style.display = 'none';
        });
    }

    if (contactCloseBtn) {
        contactCloseBtn.addEventListener('click', () => {
            contactWrapper.style.display = 'none';
            contactBtn.parentElement.style.display = 'block';
        });
    }

    if (contactSubmitBtn) {
        contactSubmitBtn.addEventListener('click', (event) => {
            event.preventDefault();
            sendContactForm();
        });
    }

    // Initialize
    if (state.isOpen) {
        toggleWindow(true);
    } else {
        windowEl.style.display = 'none';
        badge.style.display = 'flex';
    }

    updateWelcomeTime();
    loadSettings();
})();


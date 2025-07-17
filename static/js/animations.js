// =====================================================
// AURORA MOTORS - ANIMATIONS & EFFECTS
// =====================================================

document.addEventListener('DOMContentLoaded', function() {
    initializeScrollAnimations();
    initializeParallaxEffects();
    initializeCounterAnimations();
    initializeHoverEffects();
    initializePageTransitions();
});

// =====================================================
// SCROLL ANIMATIONS
// =====================================================
function initializeScrollAnimations() {
    // Initialize AOS (Animate On Scroll) if available
    if (typeof AOS !== 'undefined') {
        AOS.init({
            duration: 800,
            easing: 'ease-in-out',
            once: true,
            offset: 100,
        });
    }
    
    // Custom scroll animations for elements without AOS
    const animateElements = document.querySelectorAll('.animate-on-scroll');
    
    if (animateElements.length > 0) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animated');
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '50px'
        });
        
        animateElements.forEach(el => observer.observe(el));
    }
}

// =====================================================
// PARALLAX EFFECTS
// =====================================================
function initializeParallaxEffects() {
    const parallaxElements = document.querySelectorAll('.parallax');
    
    if (parallaxElements.length > 0) {
        const updateParallax = AuroraMotors.throttle(() => {
            const scrolled = window.pageYOffset;
            
            parallaxElements.forEach(element => {
                const rate = scrolled * -0.5;
                element.style.transform = `translateY(${rate}px)`;
            });
        }, 16); // ~60fps
        
        window.addEventListener('scroll', updateParallax);
    }
}

// =====================================================
// COUNTER ANIMATIONS
// =====================================================
function initializeCounterAnimations() {
    const counters = document.querySelectorAll('[data-count]');
    let countersAnimated = false;
    
    function animateCounters() {
        if (countersAnimated) return;
        countersAnimated = true;
        
        counters.forEach(counter => {
            const target = parseInt(counter.getAttribute('data-count'));
            const duration = 2000; // 2 seconds
            const startTime = performance.now();
            
            function updateCounter(currentTime) {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);
                
                // Easing function (ease-out)
                const easeOut = 1 - Math.pow(1 - progress, 3);
                const current = Math.floor(target * easeOut);
                
                counter.textContent = current.toLocaleString();
                
                if (progress < 1) {
                    requestAnimationFrame(updateCounter);
                } else {
                    counter.textContent = target.toLocaleString();
                }
            }
            
            requestAnimationFrame(updateCounter);
        });
    }
    
    // Trigger animation when hero section is visible
    const heroSection = document.querySelector('.hero-stats');
    if (heroSection && counters.length > 0) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    animateCounters();
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });
        
        observer.observe(heroSection);
    }
}

// =====================================================
// HOVER EFFECTS
// =====================================================
function initializeHoverEffects() {
    // Magnetic effect for buttons
    const magneticElements = document.querySelectorAll('.btn-primary, .category-card');
    
    magneticElements.forEach(element => {
        element.addEventListener('mousemove', function(e) {
            const rect = this.getBoundingClientRect();
            const x = e.clientX - rect.left - rect.width / 2;
            const y = e.clientY - rect.top - rect.height / 2;
            
            const moveX = x * 0.1;
            const moveY = y * 0.1;
            
            this.style.transform = `translate(${moveX}px, ${moveY}px)`;
        });
        
        element.addEventListener('mouseleave', function() {
            this.style.transform = 'translate(0, 0)';
        });
    });
    
    // Ripple effect for buttons
    const rippleButtons = document.querySelectorAll('.btn');
    
    rippleButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.classList.add('ripple');
            
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });
}

// =====================================================
// PAGE TRANSITIONS
// =====================================================
function initializePageTransitions() {
    // Smooth page transitions
    const links = document.querySelectorAll('a[href^="/"]');
    
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            
            // Skip if external link or has special attributes
            if (this.hasAttribute('download') || 
                this.hasAttribute('target') || 
                href.includes('#') ||
                href.includes('mailto:') ||
                href.includes('tel:')) {
                return;
            }
            
            e.preventDefault();
            
            // Add page transition effect
            document.body.classList.add('page-transitioning');
            
            setTimeout(() => {
                window.location.href = href;
            }, 300);
        });
    });
    
    // Remove transition class on page load
    window.addEventListener('load', () => {
        document.body.classList.remove('page-transitioning');
    });
}

// =====================================================
// VEHICLE CARD ANIMATIONS
// =====================================================
function initializeVehicleCardAnimations() {
    const vehicleCards = document.querySelectorAll('.vehicle-card, .vehicle-result-card');
    
    vehicleCards.forEach((card, index) => {
        // Staggered entrance animation
        card.style.animationDelay = `${index * 0.1}s`;
        
        // Hover animations
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-10px) scale(1.02)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
        
        // Image loading animation
        const image = card.querySelector('img');
        if (image) {
            image.addEventListener('load', function() {
                this.classList.add('loaded');
            });
        }
    });
}

// =====================================================
// FORM ANIMATIONS
// =====================================================
function initializeFormAnimations() {
    const formGroups = document.querySelectorAll('.form-group');
    
    formGroups.forEach(group => {
        const input = group.querySelector('input, select, textarea');
        const label = group.querySelector('label');
        
        if (input && label) {
            // Floating label effect
            function updateLabel() {
                if (input.value || input === document.activeElement) {
                    label.classList.add('active');
                } else {
                    label.classList.remove('active');
                }
            }
            
            input.addEventListener('focus', updateLabel);
            input.addEventListener('blur', updateLabel);
            input.addEventListener('input', updateLabel);
            
            // Initial state
            updateLabel();
        }
    });
}

// =====================================================
// LOADING ANIMATIONS
// =====================================================
function createLoadingSpinner(container) {
    const spinner = document.createElement('div');
    spinner.className = 'loading-spinner-overlay';
    spinner.innerHTML = `
        <div class="spinner">
            <div class="bounce1"></div>
            <div class="bounce2"></div>
            <div class="bounce3"></div>
        </div>
    `;
    
    container.appendChild(spinner);
    return spinner;
}

function removeLoadingSpinner(spinner) {
    if (spinner && spinner.parentNode) {
        spinner.classList.add('fade-out');
        setTimeout(() => {
            spinner.parentNode.removeChild(spinner);
        }, 300);
    }
}

// =====================================================
// MODAL ANIMATIONS
// =====================================================
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
        
        // Focus trap
        const focusableElements = modal.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        
        if (focusableElements.length > 0) {
            focusableElements[0].focus();
        }
    }
}

function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = '';
    }
}

// =====================================================
// TEXT ANIMATIONS
// =====================================================
function typeWriter(element, text, speed = 50) {
    let i = 0;
    element.textContent = '';
    
    function type() {
        if (i < text.length) {
            element.textContent += text.charAt(i);
            i++;
            setTimeout(type, speed);
        }
    }
    
    type();
}

// =====================================================
// EXPORT ANIMATION FUNCTIONS
// =====================================================
window.AuroraAnimations = {
    showModal,
    hideModal,
    createLoadingSpinner,
    removeLoadingSpinner,
    typeWriter,
    initializeVehicleCardAnimations,
    initializeFormAnimations
};
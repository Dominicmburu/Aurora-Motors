// // =====================================================
// // AURORA MOTORS - BOOKING FUNCTIONALITY
// // =====================================================

// document.addEventListener('DOMContentLoaded', function() {
//     initializeBookingForm();
//     initializeDateValidation();
//     initializeRealTimeSearch();
//     initializePricingCalculator();
//     initializeLocationSync();
// });

// // =====================================================
// // BOOKING FORM INITIALIZATION
// // =====================================================
// function initializeBookingForm() {
//     const bookingForm = document.getElementById('vehicle-search-form');
    
//     if (bookingForm) {
//         bookingForm.addEventListener('submit', function(e) {
//             e.preventDefault();
//             performVehicleSearch();
//         });
        
//         // Auto-search on field changes (debounced)
//         const searchInputs = bookingForm.querySelectorAll('input, select');
//         const debouncedSearch = AuroraMotors.debounce(performVehicleSearch, 500);
        
//         searchInputs.forEach(input => {
//             input.addEventListener('change', debouncedSearch);
//         });
//     }
// }

// // =====================================================
// // DATE VALIDATION
// // =====================================================
// function initializeDateValidation() {
//     const pickupDate = document.getElementById('pickup-date');
//     const dropoffDate = document.getElementById('dropoff-date');
    
//     if (pickupDate && dropoffDate) {
//         // Set minimum date to today
//         const today = new Date().toISOString().slice(0, 16);
//         pickupDate.min = today;
//         dropoffDate.min = today;
        
//         pickupDate.addEventListener('change', function() {
//             const pickupValue = this.value;
//             if (pickupValue) {
//                 // Set dropoff minimum to pickup date + 1 hour
//                 const pickupDateTime = new Date(pickupValue);
//                 pickupDateTime.setHours(pickupDateTime.getHours() + 1);
//                 dropoffDate.min = pickupDateTime.toISOString().slice(0, 16);
                
//                 // If dropoff is before new minimum, update it
//                 if (dropoffDate.value && new Date(dropoffDate.value) <= pickupDateTime) {
//                     pickupDateTime.setHours(pickupDateTime.getHours() + 23); // Add 1 day
//                     dropoffDate.value = pickupDateTime.toISOString().slice(0, 16);
//                 }
                
//                 updatePricingDisplay();
//             }
//         });
        
//         dropoffDate.addEventListener('change', function() {
//             updatePricingDisplay();
//         });
//     }
// }

// // =====================================================
// // REAL-TIME VEHICLE SEARCH
// // =====================================================
// function initializeRealTimeSearch() {
//     const searchForm = document.getElementById('vehicle-search-form');
//     const resultsContainer = document.getElementById('search-results');
    
//     if (!searchForm || !resultsContainer) return;
    
//     window.performVehicleSearch = function() {
//         const formData = new FormData(searchForm);
//         const params = new URLSearchParams();
        
//         for (let [key, value] of formData.entries()) {
//             if (value) params.append(key, value);
//         }
        
//         // Show loading state
//         showSearchLoading();
        
//         fetch(`/api/search/?${params.toString()}`)
//             .then(response => response.json())
//             .then(data => {
//                 if (data.success) {
//                     displaySearchResults(data);
//                 } else {
//                     showSearchError(data.error);
//                 }
//             })
//             .catch(error => {
//                 console.error('Search error:', error);
//                 showSearchError('An error occurred while searching. Please try again.');
//             });
//     };
// }

// function showSearchLoading() {
//     const resultsContainer = document.getElementById('search-results');
//     resultsContainer.innerHTML = `
//         <div class="search-loading">
//             <div class="loading-spinner"></div>
//             <p>Searching available vehicles...</p>
//         </div>
//     `;
// }

// function displaySearchResults(data) {
//     const resultsContainer = document.getElementById('search-results');
    
//     if (data.vehicles.length === 0) {
//         resultsContainer.innerHTML = `
//             <div class="no-results">
//                 <i class="fas fa-car"></i>
//                 <h3>No vehicles available</h3>
//                 <p>Try adjusting your search criteria or dates.</p>
//             </div>
//         `;
//         return;
//     }
    
//     const vehiclesHTML = data.vehicles.map(vehicle => `
//         <div class="vehicle-result-card" data-vehicle-id="${vehicle.id}">
//             <div class="vehicle-image">
//                 <img src="${vehicle.image || '/static/images/default-car.jpg'}" 
//                      alt="${vehicle.name}" loading="lazy">
//                 <div class="vehicle-category">${vehicle.category}</div>
//             </div>
//             <div class="vehicle-details">
//                 <h3 class="vehicle-name">${vehicle.name}</h3>
//                 <div class="vehicle-specs">
//                     <span><i class="fas fa-users"></i> ${vehicle.seats} seats</span>
//                     <span><i class="fas fa-cog"></i> ${vehicle.transmission}</span>
//                     <span><i class="fas fa-gas-pump"></i> ${vehicle.fuel_type}</span>
//                 </div>
//                 <div class="vehicle-pricing">
//                     <div class="daily-rate">$${vehicle.daily_rate}/day</div>
//                     <div class="total-price">Total: $${vehicle.total_price} (${data.total_days} days)</div>
//                 </div>
//                 <div class="vehicle-actions">
//                     <button class="btn btn-outline btn-small" onclick="viewVehicleDetails('${vehicle.id}')">
//                         View Details
//                     </button>
//                     <button class="btn btn-primary btn-small" onclick="selectVehicle('${vehicle.id}')">
//                         Select Vehicle
//                     </button>
//                 </div>
//             </div>
//         </div>
//     `).join('');
    
//     resultsContainer.innerHTML = `
//         <div class="search-results-header">
//             <h3>Available Vehicles (${data.vehicles.length})</h3>
//             <div class="results-filters">
//                 <select id="sort-results">
//                     <option value="price">Price: Low to High</option>
//                     <option value="price-desc">Price: High to Low</option>
//                     <option value="name">Name</option>
//                     <option value="category">Category</option>
//                 </select>
//             </div>
//         </div>
//         <div class="vehicles-grid">
//             ${vehiclesHTML}
//         </div>
//     `;
    
//     // Initialize sorting
//     document.getElementById('sort-results').addEventListener('change', function() {
//         sortSearchResults(this.value);
//     });
// }

// function showSearchError(message) {
//     const resultsContainer = document.getElementById('search-results');
//     resultsContainer.innerHTML = `
//         <div class="search-error">
//             <i class="fas fa-exclamation-circle"></i>
//             <h3>Search Error</h3>
//             <p>${message}</p>
//             <button class="btn btn-primary" onclick="performVehicleSearch()">Try Again</button>
//         </div>
//     `;
// }

// // =====================================================
// // PRICING CALCULATOR
// // =====================================================
// function initializePricingCalculator() {
//     window.updatePricingDisplay = function() {
//         const pickupDate = document.getElementById('pickup-date');
//         const dropoffDate = document.getElementById('dropoff-date');
//         const pricingDisplay = document.getElementById('pricing-display');
        
//         if (!pickupDate || !dropoffDate || !pricingDisplay) return;
        
//         const pickup = pickupDate.value;
//         const dropoff = dropoffDate.value;
        
//         if (pickup && dropoff) {
//             const pickupDateTime = new Date(pickup);
//             const dropoffDateTime = new Date(dropoff);
//             const timeDiff = dropoffDateTime.getTime() - pickupDateTime.getTime();
//             const daysDiff = Math.ceil(timeDiff / (1000 * 3600 * 24));
            
//             if (daysDiff > 0) {
//                 pricingDisplay.innerHTML = `
//                     <div class="rental-period">
//                         <i class="fas fa-calendar-alt"></i>
//                         <span>${daysDiff} day${daysDiff > 1 ? 's' : ''}</span>
//                     </div>
//                 `;
//             }
//         }
//     };
// }

// // =====================================================
// // LOCATION SYNCHRONIZATION
// // =====================================================
// function initializeLocationSync() {
//     const pickupLocation = document.getElementById('pickup-location');
//     const dropoffLocation = document.getElementById('dropoff-location');
//     const sameLocationCheckbox = document.getElementById('same-location');
    
//     if (pickupLocation && dropoffLocation) {
//         // Option to use same location for dropoff
//         if (sameLocationCheckbox) {
//             sameLocationCheckbox.addEventListener('change', function() {
//                 if (this.checked) {
//                     dropoffLocation.value = pickupLocation.value;
//                     dropoffLocation.disabled = true;
//                 } else {
//                     dropoffLocation.disabled = false;
//                 }
//             });
//         }
        
//         pickupLocation.addEventListener('change', function() {
//             if (sameLocationCheckbox && sameLocationCheckbox.checked) {
//                 dropoffLocation.value = this.value;
//             }
//         });
//     }
// }

// // =====================================================
// // VEHICLE SELECTION
// // =====================================================
// window.viewVehicleDetails = function(vehicleId) {
//     // Store search parameters in session
//     storeSearchParameters();
    
//     // Redirect to vehicle detail page
//     window.location.href = `/vehicle/${vehicleId}/`;
// };

// window.selectVehicle = function(vehicleId) {
//     // Store search parameters in session
//     storeSearchParameters();
    
//     // Redirect to booking page
//     window.location.href = `/book/${vehicleId}/`;
// };

// function storeSearchParameters() {
//     const form = document.getElementById('vehicle-search-form');
//     if (form) {
//         const formData = new FormData(form);
//         const params = {};
        
//         for (let [key, value] of formData.entries()) {
//             if (value) params[key] = value;
//         }
        
//         sessionStorage.setItem('searchParams', JSON.stringify(params));
//     }
// }

// // =====================================================
// // SORTING FUNCTIONALITY
// // =====================================================
// function sortSearchResults(sortBy) {
//     const grid = document.querySelector('.vehicles-grid');
//     const cards = Array.from(grid.querySelectorAll('.vehicle-result-card'));
    
//     cards.sort((a, b) => {
//         switch (sortBy) {
//             case 'price':
//                 return getVehiclePrice(a) - getVehiclePrice(b);
//             case 'price-desc':
//                 return getVehiclePrice(b) - getVehiclePrice(a);
//             case 'name':
//                 return getVehicleName(a).localeCompare(getVehicleName(b));
//             case 'category':
//                 return getVehicleCategory(a).localeCompare(getVehicleCategory(b));
//             default:
//                 return 0;
//         }
//     });
    
//     // Re-append sorted cards
//     cards.forEach(card => grid.appendChild(card));
// }

// function getVehiclePrice(card) {
//     const priceText = card.querySelector('.daily-rate').textContent;
//     return parseFloat(priceText.replace('$', '').replace('/day', ''));
// }

// function getVehicleName(card) {
//     return card.querySelector('.vehicle-name').textContent;
// }

// function getVehicleCategory(card) {
//     return card.querySelector('.vehicle-category').textContent;
// }

// // =====================================================
// // BOOKING CONFIRMATION
// // =====================================================
// function initializeBookingConfirmation() {
//     const confirmBookingBtn = document.getElementById('confirm-booking');
    
//     if (confirmBookingBtn) {
//         confirmBookingBtn.addEventListener('click', function() {
//             const bookingData = collectBookingData();
            
//             if (validateBookingData(bookingData)) {
//                 submitBooking(bookingData);
//             }
//         });
//     }
// }

// function collectBookingData() {
//     // Collect all booking form data
//     return {
//         vehicle_id: document.getElementById('vehicle-id').value,
//         pickup_date: document.getElementById('pickup-date').value,
//         dropoff_date: document.getElementById('dropoff-date').value,
//         pickup_location: document.getElementById('pickup-location').value,
//         dropoff_location: document.getElementById('dropoff-location').value,
//         special_requests: document.getElementById('special-requests').value,
//     };
// }

// function validateBookingData(data) {
//     // Validate booking data before submission
//     if (!data.pickup_date || !data.dropoff_date) {
//         AuroraMotors.showNotification('Please select pickup and dropoff dates', 'error');
//         return false;
//     }
    
//     if (!data.pickup_location || !data.dropoff_location) {
//         AuroraMotors.showNotification('Please select pickup and dropoff locations', 'error');
//         return false;
//     }
    
//     return true;
// }

// function submitBooking(data) {
//     // Show loading state
//     const confirmBtn = document.getElementById('confirm-booking');
//     const originalText = confirmBtn.textContent;
//     confirmBtn.textContent = 'Processing...';
//     confirmBtn.disabled = true;
    
//     fetch('/api/booking/create/', {
//         method: 'POST',
//         headers: {
//             'Content-Type': 'application/json',
//             'X-CSRFToken': getCsrfToken(),
//         },
//         body: JSON.stringify(data)
//     })
//     .then(response => response.json())
//     .then(result => {
//         if (result.success) {
//             window.location.href = `/booking/${result.booking_id}/confirmation/`;
//         } else {
//             AuroraMotors.showNotification(result.error || 'Booking failed', 'error');
//         }
//     })
//     .catch(error => {
//         console.error('Booking error:', error);
//         AuroraMotors.showNotification('An error occurred. Please try again.', 'error');
//     })
//     .finally(() => {
//         confirmBtn.textContent = originalText;
//         confirmBtn.disabled = false;
//     });
// }

// function getCsrfToken() {
//     return document.querySelector('[name=csrfmiddlewaretoken]').value;
// }



// =====================================================
// AURORA MOTORS - MAIN JAVASCRIPT
// =====================================================

// Define global AuroraMotors object IMMEDIATELY at the top
window.AuroraMotors = window.AuroraMotors || {};

// Initialize core functions right away
window.AuroraMotors.showNotification = function(message, type = 'info', duration = 5000) {
    console.log(`${type.toUpperCase()}: ${message}`);
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <i class="fas fa-${getNotificationIcon(type)}"></i>
            <span>${message}</span>
            <button class="notification-close">×</button>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Show notification
    setTimeout(() => notification.classList.add('show'), 100);
    
    // Auto hide
    setTimeout(() => hideNotification(notification), duration);
    
    // Manual close
    const closeBtn = notification.querySelector('.notification-close');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            hideNotification(notification);
        });
    }
    
    function hideNotification(notification) {
        notification.classList.remove('show');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }
    
    function getNotificationIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || icons.info;
    }
};

window.AuroraMotors.debounce = function(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
};

window.AuroraMotors.throttle = function(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    }
};

window.AuroraMotors.validateForm = function(form) {
    let isValid = true;
    const inputs = form.querySelectorAll('input, select, textarea');
    
    inputs.forEach(input => {
        if (!validateField(input)) {
            isValid = false;
        }
    });
    
    return isValid;
};

// Now initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize all components
    initializeHeader();
    initializeLoadingScreen();
    initializeMobileMenu();
    initializeUserMenu();
    initializeBackToTop();
    initializeFormValidation();
    initializeImageLazyLoading();
    initializeSmoothScroll();
});

// =====================================================
// HEADER FUNCTIONALITY
// =====================================================
function initializeHeader() {
    const header = document.getElementById('header');
    if (!header) return;
    
    let lastScrollTop = 0;
    
    window.addEventListener('scroll', function() {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        // Add scrolled class for styling
        if (scrollTop > 50) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }
        
        // Hide/show header on scroll
        if (scrollTop > lastScrollTop && scrollTop > 100) {
            header.style.transform = 'translateY(-100%)';
        } else {
            header.style.transform = 'translateY(0)';
        }
        
        lastScrollTop = scrollTop;
    });
}

// =====================================================
// LOADING SCREEN
// =====================================================
function initializeLoadingScreen() {
    const loadingScreen = document.getElementById('loading-screen');
    
    if (loadingScreen) {
        window.addEventListener('load', function() {
            setTimeout(() => {
                loadingScreen.classList.add('hidden');
                
                // Remove from DOM after animation
                setTimeout(() => {
                    if (loadingScreen.parentNode) {
                        loadingScreen.parentNode.removeChild(loadingScreen);
                    }
                }, 500);
            }, 1000);
        });
    }
}

// =====================================================
// MOBILE MENU
// =====================================================
function initializeMobileMenu() {
    const navToggle = document.getElementById('nav-toggle');
    const navMenu = document.getElementById('nav-menu');
    
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
            navToggle.classList.toggle('active');
            
            // Prevent body scroll when menu is open
            document.body.style.overflow = navMenu.classList.contains('active') ? 'hidden' : '';
        });
        
        // Close menu when clicking outside
        document.addEventListener('click', function(e) {
            if (!navMenu.contains(e.target) && !navToggle.contains(e.target)) {
                navMenu.classList.remove('active');
                navToggle.classList.remove('active');
                document.body.style.overflow = '';
            }
        });
        
        // Close menu on window resize
        window.addEventListener('resize', function() {
            if (window.innerWidth > 768) {
                navMenu.classList.remove('active');
                navToggle.classList.remove('active');
                document.body.style.overflow = '';
            }
        });
    }
}

// =====================================================
// USER MENU DROPDOWN
// =====================================================
function initializeUserMenu() {
    const userMenuToggles = document.querySelectorAll('.user-menu-toggle');
    
    userMenuToggles.forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            const dropdown = this.nextElementSibling;
            if (!dropdown) return;
            
            const isOpen = dropdown.style.opacity === '1';
            
            // Close all dropdowns
            document.querySelectorAll('.user-dropdown').forEach(dd => {
                dd.style.opacity = '0';
                dd.style.visibility = 'hidden';
                dd.style.transform = 'translateY(-10px)';
            });
            
            // Open current dropdown if it was closed
            if (!isOpen) {
                dropdown.style.opacity = '1';
                dropdown.style.visibility = 'visible';
                dropdown.style.transform = 'translateY(0)';
            }
        });
    });
    
    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.user-menu')) {
            document.querySelectorAll('.user-dropdown').forEach(dropdown => {
                dropdown.style.opacity = '0';
                dropdown.style.visibility = 'hidden';
                dropdown.style.transform = 'translateY(-10px)';
            });
        }
    });
}

// =====================================================
// BACK TO TOP BUTTON
// =====================================================
function initializeBackToTop() {
    const backToTopBtn = document.getElementById('back-to-top');
    
    if (backToTopBtn) {
        window.addEventListener('scroll', function() {
            if (window.pageYOffset > 300) {
                backToTopBtn.classList.add('visible');
            } else {
                backToTopBtn.classList.remove('visible');
            }
        });
        
        backToTopBtn.addEventListener('click', function() {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }
}

// =====================================================
// FORM VALIDATION
// =====================================================
function initializeFormValidation() {
    const forms = document.querySelectorAll('form[data-validate]');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!window.AuroraMotors.validateForm(this)) {
                e.preventDefault();
            }
        });
        
        // Real-time validation
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                validateField(this);
            });
            
            input.addEventListener('input', function() {
                if (this.classList.contains('error')) {
                    validateField(this);
                }
            });
        });
    });
}

function validateField(field) {
    const value = field.value.trim();
    const type = field.type;
    const required = field.hasAttribute('required');
    let isValid = true;
    let errorMessage = '';
    
    // Clear previous errors
    clearFieldError(field);
    
    // Required validation
    if (required && !value) {
        isValid = false;
        errorMessage = 'This field is required';
    }
    
    // Email validation
    if (type === 'email' && value) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value)) {
            isValid = false;
            errorMessage = 'Please enter a valid email address';
        }
    }
    
    // Phone validation
    if (field.name === 'phone' && value) {
        const phoneRegex = /^[\+]?[1-9][\d]{0,15}$/;
        if (!phoneRegex.test(value.replace(/\s/g, ''))) {
            isValid = false;
            errorMessage = 'Please enter a valid phone number';
        }
    }
    
    // Date validation
    if (type === 'date' || type === 'datetime-local') {
        const selectedDate = new Date(value);
        const today = new Date();
        
        if (field.name.includes('start') || field.name.includes('pickup')) {
            if (selectedDate < today) {
                isValid = false;
                errorMessage = 'Date cannot be in the past';
            }
        }
    }
    
    // Display error
    if (!isValid) {
        showFieldError(field, errorMessage);
    }
    
    return isValid;
}

function showFieldError(field, message) {
    field.classList.add('error');
    
    let errorElement = field.parentNode.querySelector('.error-message');
    if (!errorElement) {
        errorElement = document.createElement('div');
        errorElement.className = 'error-message';
        field.parentNode.appendChild(errorElement);
    }
    
    errorElement.textContent = message;
}

function clearFieldError(field) {
    field.classList.remove('error');
    const errorElement = field.parentNode.querySelector('.error-message');
    if (errorElement) {
        errorElement.remove();
    }
}

// =====================================================
// IMAGE LAZY LOADING
// =====================================================
function initializeImageLazyLoading() {
    const images = document.querySelectorAll('img[data-src]');
    
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    imageObserver.unobserve(img);
                }
            });
        });
        
        images.forEach(img => imageObserver.observe(img));
    } else {
        // Fallback for older browsers
        images.forEach(img => {
            img.src = img.dataset.src;
            img.classList.remove('lazy');
        });
    }
}

// =====================================================
// SMOOTH SCROLL
// =====================================================
function initializeSmoothScroll() {
    const links = document.querySelectorAll('a[href^="#"]');
    
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            
            if (targetElement) {
                const header = document.querySelector('.header');
                const headerHeight = header ? header.offsetHeight : 0;
                const targetPosition = targetElement.offsetTop - headerHeight;
                
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });
}
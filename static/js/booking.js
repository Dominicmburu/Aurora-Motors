// =====================================================
// AURORA MOTORS - BOOKING FUNCTIONALITY
// =====================================================

// Self-contained booking system that doesn't depend on main.js initialization
(function() {
    'use strict';
    
    // Ensure AuroraMotors exists with required functions
    function ensureAuroraMotors() {
        if (typeof window.AuroraMotors === 'undefined') {
            console.log('Creating AuroraMotors fallback for booking system...');
            window.AuroraMotors = {};
        }
        
        if (!window.AuroraMotors.debounce) {
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
        }
        
        if (!window.AuroraMotors.showNotification) {
            window.AuroraMotors.showNotification = function(message, type = 'info') {
                console.log(`${type.toUpperCase()}: ${message}`);
                // Simple fallback notification
                if (typeof toastr !== 'undefined') {
                    toastr[type](message);
                } else {
                    alert(`${type.toUpperCase()}: ${message}`);
                }
            };
        }
    }
    
    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        console.log('Initializing booking system...');
        
        // Ensure AuroraMotors is available
        ensureAuroraMotors();
        
        // Initialize booking functionality
        initializeBookingForm();
        initializeDateValidation();
        initializeRealTimeSearch();
        initializePricingCalculator();
        initializeLocationSync();
        
        console.log('Booking system initialized successfully');
    });

    // =====================================================
    // BOOKING FORM INITIALIZATION
    // =====================================================
    function initializeBookingForm() {
        const bookingForm = document.getElementById('vehicle-search-form');
        
        if (bookingForm) {
            console.log('Initializing booking form...');
            
            bookingForm.addEventListener('submit', function(e) {
                e.preventDefault();
                console.log('Form submitted, performing search...');
                performVehicleSearch();
            });
            
            // Auto-search on field changes (debounced)
            const searchInputs = bookingForm.querySelectorAll('input, select');
            
            if (window.AuroraMotors && window.AuroraMotors.debounce) {
                const debouncedSearch = window.AuroraMotors.debounce(performVehicleSearch, 500);
                
                searchInputs.forEach(input => {
                    input.addEventListener('change', debouncedSearch);
                });
            } else {
                console.warn('Debounce function not available, skipping auto-search');
            }
        }
    }

    // =====================================================
    // DATE VALIDATION
    // =====================================================
    function initializeDateValidation() {
        const pickupDate = document.getElementById('pickup-date');
        const dropoffDate = document.getElementById('dropoff-date');
        
        if (pickupDate && dropoffDate) {
            console.log('Initializing date validation...');
            
            // Set minimum date to today
            const today = new Date().toISOString().slice(0, 16);
            pickupDate.min = today;
            dropoffDate.min = today;
            
            pickupDate.addEventListener('change', function() {
                const pickupValue = this.value;
                if (pickupValue) {
                    // Set dropoff minimum to pickup date + 1 hour
                    const pickupDateTime = new Date(pickupValue);
                    pickupDateTime.setHours(pickupDateTime.getHours() + 1);
                    dropoffDate.min = pickupDateTime.toISOString().slice(0, 16);
                    
                    // If dropoff is before new minimum, update it
                    if (dropoffDate.value && new Date(dropoffDate.value) <= pickupDateTime) {
                        pickupDateTime.setHours(pickupDateTime.getHours() + 23); // Add 1 day
                        dropoffDate.value = pickupDateTime.toISOString().slice(0, 16);
                    }
                    
                    updatePricingDisplay();
                }
            });
            
            dropoffDate.addEventListener('change', function() {
                updatePricingDisplay();
            });
        }
    }

    // =====================================================
    // REAL-TIME VEHICLE SEARCH
    // =====================================================
    function initializeRealTimeSearch() {
        const searchForm = document.getElementById('vehicle-search-form');
        
        if (searchForm) {
            console.log('Initializing real-time search...');
        }
    }

    // Define the search function
    function performVehicleSearch() {
        console.log('Performing vehicle search...');
        
        const searchForm = document.getElementById('vehicle-search-form');
        if (!searchForm) {
            console.error('Search form not found');
            return;
        }
        
        const formData = new FormData(searchForm);
        const params = new URLSearchParams();
        
        for (let [key, value] of formData.entries()) {
            if (value) params.append(key, value);
        }
        
        console.log('Search parameters:', params.toString());
        
        // Show loading state
        showSearchLoading();
        
        fetch(`/api/search/?${params.toString()}`)
            .then(response => {
                console.log('Search response received:', response.status);
                return response.json();
            })
            .then(data => {
                console.log('Search data:', data);
                if (data.success) {
                    displaySearchResults(data);
                } else {
                    showSearchError(data.error || 'Search failed');
                }
            })
            .catch(error => {
                console.error('Search error:', error);
                showSearchError('An error occurred while searching. Please try again.');
            });
    }

    function showSearchLoading() {
        const resultsContainer = document.getElementById('search-results');
        if (resultsContainer) {
            resultsContainer.innerHTML = `
                <div class="search-loading">
                    <div class="loading-spinner"></div>
                    <p>Searching available vehicles...</p>
                </div>
            `;
        }
    }

    function displaySearchResults(data) {
        const resultsContainer = document.getElementById('search-results');
        if (!resultsContainer) {
            console.error('Results container not found');
            return;
        }
        
        if (data.vehicles.length === 0) {
            resultsContainer.innerHTML = `
                <div class="no-results">
                    <i class="fas fa-car"></i>
                    <h3>No vehicles available</h3>
                    <p>Try adjusting your search criteria or dates.</p>
                </div>
            `;
            return;
        }
        
        const vehiclesHTML = data.vehicles.map(vehicle => `
            <div class="vehicle-result-card" data-vehicle-id="${vehicle.id}">
                <div class="vehicle-image">
                    <img src="${vehicle.image || 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200"><rect width="400" height="200" fill="%23f0f0f0"/><text x="200" y="100" text-anchor="middle" fill="%23666" font-family="Arial" font-size="16">No Image</text></svg>'}" 
                         alt="${vehicle.name}" loading="lazy">
                    <div class="vehicle-category">${vehicle.category}</div>
                </div>
                <div class="vehicle-details">
                    <h3 class="vehicle-name">${vehicle.name}</h3>
                    <div class="vehicle-specs">
                        <span><i class="fas fa-users"></i> ${vehicle.seats} seats</span>
                        <span><i class="fas fa-cog"></i> ${vehicle.transmission}</span>
                        <span><i class="fas fa-gas-pump"></i> ${vehicle.fuel_type}</span>
                    </div>
                    <div class="vehicle-pricing">
                        <div class="daily-rate">$${vehicle.daily_rate}/day</div>
                        <div class="total-price">Total: $${vehicle.total_price} (${data.total_days} days)</div>
                    </div>
                    <div class="vehicle-actions">
                        <button class="btn btn-outline btn-small" onclick="viewVehicleDetails('${vehicle.id}')">
                            View Details
                        </button>
                        <button class="btn btn-primary btn-small" onclick="selectVehicle('${vehicle.id}')">
                            Select Vehicle
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
        
        resultsContainer.innerHTML = `
            <div class="search-results-header">
                <h3>Available Vehicles (${data.vehicles.length})</h3>
                <div class="results-filters">
                    <select id="sort-results">
                        <option value="price">Price: Low to High</option>
                        <option value="price-desc">Price: High to Low</option>
                        <option value="name">Name</option>
                        <option value="category">Category</option>
                    </select>
                </div>
            </div>
            <div class="vehicles-grid">
                ${vehiclesHTML}
            </div>
        `;
        
        // Initialize sorting
        const sortSelect = document.getElementById('sort-results');
        if (sortSelect) {
            sortSelect.addEventListener('change', function() {
                sortSearchResults(this.value);
            });
        }
    }

    function showSearchError(message) {
        const resultsContainer = document.getElementById('search-results');
        if (resultsContainer) {
            resultsContainer.innerHTML = `
                <div class="search-error">
                    <i class="fas fa-exclamation-circle"></i>
                    <h3>Search Error</h3>
                    <p>${message}</p>
                    <button class="btn btn-primary" onclick="performVehicleSearch()">Try Again</button>
                </div>
            `;
        }
    }

    // =====================================================
    // PRICING CALCULATOR
    // =====================================================
    function initializePricingCalculator() {
        console.log('Initializing pricing calculator...');
    }

    function updatePricingDisplay() {
        const pickupDate = document.getElementById('pickup-date');
        const dropoffDate = document.getElementById('dropoff-date');
        const pricingDisplay = document.getElementById('pricing-display');
        
        if (!pickupDate || !dropoffDate || !pricingDisplay) return;
        
        const pickup = pickupDate.value;
        const dropoff = dropoffDate.value;
        
        if (pickup && dropoff) {
            const pickupDateTime = new Date(pickup);
            const dropoffDateTime = new Date(dropoff);
            const timeDiff = dropoffDateTime.getTime() - pickupDateTime.getTime();
            const daysDiff = Math.ceil(timeDiff / (1000 * 3600 * 24));
            
            if (daysDiff > 0) {
                pricingDisplay.innerHTML = `
                    <div class="rental-period">
                        <i class="fas fa-calendar-alt"></i>
                        <span>${daysDiff} day${daysDiff > 1 ? 's' : ''}</span>
                    </div>
                `;
            }
        }
    }

    // =====================================================
    // LOCATION SYNCHRONIZATION
    // =====================================================
    function initializeLocationSync() {
        const pickupLocation = document.getElementById('pickup-location');
        const dropoffLocation = document.getElementById('dropoff-location');
        const sameLocationCheckbox = document.getElementById('same-location');
        
        if (pickupLocation && dropoffLocation) {
            console.log('Initializing location sync...');
            
            // Option to use same location for dropoff
            if (sameLocationCheckbox) {
                sameLocationCheckbox.addEventListener('change', function() {
                    if (this.checked) {
                        dropoffLocation.value = pickupLocation.value;
                        dropoffLocation.disabled = true;
                    } else {
                        dropoffLocation.disabled = false;
                    }
                });
            }
            
            pickupLocation.addEventListener('change', function() {
                if (sameLocationCheckbox && sameLocationCheckbox.checked) {
                    dropoffLocation.value = this.value;
                }
            });
        }
    }

    // =====================================================
    // GLOBAL FUNCTIONS (for onclick handlers)
    // =====================================================
    
    // Make functions globally available
    window.performVehicleSearch = performVehicleSearch;
    
    window.viewVehicleDetails = function(vehicleId) {
        console.log('Viewing vehicle details:', vehicleId);
        storeSearchParameters();
        window.location.href = `/vehicle/${vehicleId}/`;
    };

    window.selectVehicle = function(vehicleId) {
        console.log('Selecting vehicle:', vehicleId);
        storeSearchParameters();
        window.location.href = `/book/${vehicleId}/`;
    };

    function storeSearchParameters() {
        const form = document.getElementById('vehicle-search-form');
        if (form) {
            const formData = new FormData(form);
            const params = {};
            
            for (let [key, value] of formData.entries()) {
                if (value) params[key] = value;
            }
            
            sessionStorage.setItem('searchParams', JSON.stringify(params));
            console.log('Stored search parameters:', params);
        }
    }

    // =====================================================
    // SORTING FUNCTIONALITY
    // =====================================================
    function sortSearchResults(sortBy) {
        const grid = document.querySelector('.vehicles-grid');
        if (!grid) return;
        
        const cards = Array.from(grid.querySelectorAll('.vehicle-result-card'));
        
        cards.sort((a, b) => {
            switch (sortBy) {
                case 'price':
                    return getVehiclePrice(a) - getVehiclePrice(b);
                case 'price-desc':
                    return getVehiclePrice(b) - getVehiclePrice(a);
                case 'name':
                    return getVehicleName(a).localeCompare(getVehicleName(b));
                case 'category':
                    return getVehicleCategory(a).localeCompare(getVehicleCategory(b));
                default:
                    return 0;
            }
        });
        
        // Re-append sorted cards
        cards.forEach(card => grid.appendChild(card));
    }

    function getVehiclePrice(card) {
        const dailyRateElement = card.querySelector('.daily-rate');
        if (!dailyRateElement) return 0;
        const priceText = dailyRateElement.textContent;
        return parseFloat(priceText.replace('$', '').replace('/day', ''));
    }

    function getVehicleName(card) {
        const nameElement = card.querySelector('.vehicle-name');
        return nameElement ? nameElement.textContent : '';
    }

    function getVehicleCategory(card) {
        const categoryElement = card.querySelector('.vehicle-category');
        return categoryElement ? categoryElement.textContent : '';
    }

})();
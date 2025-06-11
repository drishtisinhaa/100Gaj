// Delhi Area Analyzer - Main JavaScript

class DelhiAreaAnalyzer {
    constructor() {
        this.searchInput = document.getElementById('locationSearch');
        this.searchDropdown = document.getElementById('searchDropdown');
        this.loadingIndicator = document.getElementById('loadingIndicator');
        this.locationDetails = document.getElementById('locationDetails');
        this.errorMessage = document.getElementById('errorMessage');
        
        this.searchTimeout = null;
        this.selectedLocationIndex = -1;
        this.searchResults = [];
        
        this.initializeEventListeners();
    }
    
    initializeEventListeners() {
        // Search input events
        this.searchInput.addEventListener('input', (e) => {
            this.handleSearchInput(e.target.value);
        });
        
        this.searchInput.addEventListener('keydown', (e) => {
            this.handleKeyNavigation(e);
        });
        
        this.searchInput.addEventListener('blur', (e) => {
            // Delay hiding dropdown to allow click events
            setTimeout(() => {
                this.hideDropdown();
            }, 200);
        });
        
        // Click outside to hide dropdown
        document.addEventListener('click', (e) => {
            if (!e.target.closest('#locationSearch') && !e.target.closest('#searchDropdown')) {
                this.hideDropdown();
            }
        });
    }
    
    handleSearchInput(query) {
        clearTimeout(this.searchTimeout);
        
        if (query.length < 2) {
            this.hideDropdown();
            return;
        }
        
        this.searchTimeout = setTimeout(() => {
            this.searchLocations(query);
        }, 300);
    }
    
    async searchLocations(query) {
        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
            
            if (!response.ok) {
                throw new Error('Search failed');
            }
            
            const results = await response.json();
            this.displaySearchResults(results);
            
        } catch (error) {
            console.error('Search error:', error);
            this.showError('Failed to search locations. Please try again.');
        }
    }
    
    displaySearchResults(results) {
        this.searchResults = results;
        this.selectedLocationIndex = -1;
        
        if (results.length === 0) {
            this.hideDropdown();
            return;
        }
        
        let html = '';
        results.forEach((result, index) => {
            const safetyColor = this.getSafetyColor(result.safety_rating);
            const crimeColor = this.getCrimeColor(result.crime_level);
            
            html += `
                <div class="dropdown-item search-result-item" data-index="${index}">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${result.location}</strong>
                            <small class="text-muted d-block">${result.zone}</small>
                        </div>
                        <div class="text-end">
                            <span class="badge ${safetyColor} me-1">Safety: ${result.safety_rating}/10</span>
                            <span class="badge ${crimeColor}">${result.crime_level}</span>
                        </div>
                    </div>
                </div>
            `;
        });
        
        this.searchDropdown.innerHTML = html;
        this.showDropdown();
        
        // Add click event listeners to search results
        this.searchDropdown.querySelectorAll('.search-result-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const index = parseInt(e.currentTarget.dataset.index);
                this.selectLocation(index);
            });
        });
    }
    
    handleKeyNavigation(e) {
        const items = this.searchDropdown.querySelectorAll('.search-result-item');
        
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            this.selectedLocationIndex = Math.min(this.selectedLocationIndex + 1, items.length - 1);
            this.updateSelection(items);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            this.selectedLocationIndex = Math.max(this.selectedLocationIndex - 1, -1);
            this.updateSelection(items);
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (this.selectedLocationIndex >= 0) {
                this.selectLocation(this.selectedLocationIndex);
            }
        } else if (e.key === 'Escape') {
            this.hideDropdown();
        }
    }
    
    updateSelection(items) {
        items.forEach((item, index) => {
            if (index === this.selectedLocationIndex) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
    }
    
    selectLocation(index) {
        if (index >= 0 && index < this.searchResults.length) {
            const location = this.searchResults[index];
            this.searchInput.value = location.location;
            this.hideDropdown();
            this.loadLocationDetails(location.location);
        }
    }
    
    async loadLocationDetails(locationName) {
        this.showLoading();
        this.hideError();
        
        try {
            const response = await fetch(`/api/location/${encodeURIComponent(locationName)}`);
            
            if (!response.ok) {
                if (response.status === 404) {
                    throw new Error('Location not found');
                } else {
                    throw new Error('Failed to load location details');
                }
            }
            
            const locationData = await response.json();
            this.displayLocationDetails(locationData);
            
        } catch (error) {
            console.error('Location details error:', error);
            this.showError(error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    displayLocationDetails(data) {
        // Update location header
        document.getElementById('locationName').textContent = data.location;
        document.getElementById('locationZone').textContent = data.zone;
        
        // Update crime level badge
        const crimeLevelBadge = document.getElementById('crimeLevel');
        crimeLevelBadge.textContent = data.crime_level;
        crimeLevelBadge.className = `badge fs-6 me-2 ${this.getCrimeColor(data.crime_level)}`;
        
        // Update statistics
        document.getElementById('safetyRating').textContent = data.safety_rating.toFixed(1);
        document.getElementById('crimeRating').textContent = data.crime_rating.toFixed(1);
        document.getElementById('totalCrimes').textContent = data.total_crimes.toLocaleString();
        document.getElementById('waterIssues').textContent = data.water_clogging || 'Not specified';
        
        // Update pros list
        const prosList = document.getElementById('prosList');
        prosList.innerHTML = '';
        data.pros.forEach(pro => {
            const li = document.createElement('li');
            li.innerHTML = `<i class="fas fa-check-circle text-success me-2"></i>${pro}`;
            li.className = 'mb-2';
            prosList.appendChild(li);
        });
        
        // Update cons list
        const consList = document.getElementById('consList');
        consList.innerHTML = '';
        data.cons.forEach(con => {
            const li = document.createElement('li');
            li.innerHTML = `<i class="fas fa-times-circle text-danger me-2"></i>${con}`;
            li.className = 'mb-2';
            consList.appendChild(li);
        });
        
        // Update infrastructure info
        document.getElementById('waterClogging').textContent = data.water_clogging || 'Not specified';
        document.getElementById('electricityIssues').textContent = data.electricity_issues || 'Not specified';
        
        // Show location details
        this.locationDetails.style.display = 'block';
        
        // Scroll to details
        this.locationDetails.scrollIntoView({ behavior: 'smooth' });
    }
    
    getSafetyColor(rating) {
        if (rating >= 8) return 'bg-success';
        if (rating >= 6) return 'bg-warning';
        return 'bg-danger';
    }
    
    getCrimeColor(level) {
        switch (level.toLowerCase()) {
            case 'low': return 'bg-success';
            case 'medium': return 'bg-warning';
            case 'high': return 'bg-danger';
            default: return 'bg-secondary';
        }
    }
    
    showDropdown() {
        this.searchDropdown.style.display = 'block';
    }
    
    hideDropdown() {
        this.searchDropdown.style.display = 'none';
    }
    
    showLoading() {
        this.loadingIndicator.style.display = 'block';
        this.locationDetails.style.display = 'none';
    }
    
    hideLoading() {
        this.loadingIndicator.style.display = 'none';
    }
    
    showError(message) {
        document.getElementById('errorText').textContent = message;
        this.errorMessage.style.display = 'block';
        this.locationDetails.style.display = 'none';
    }
    
    hideError() {
        this.errorMessage.style.display = 'none';
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new DelhiAreaAnalyzer();
});

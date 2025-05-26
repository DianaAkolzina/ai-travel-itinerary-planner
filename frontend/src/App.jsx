import React, { useState, useCallback } from 'react';
import Map from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';
import { 
  MapPin, Calendar, Globe, Target, ExternalLink, Clock, 
  Loader2, AlertCircle, CheckCircle, Route, Star, 
  Cloud, Sun, CloudRain, Thermometer, Droplets, Wind,
  CalendarDays, CalendarRange
} from 'lucide-react';

const INTEREST_OPTIONS = [
  'Food', 'Art', 'History', 'Nature', 'Architecture',
  'Beaches', 'Nightlife', 'Shopping', 'Museums', 'Hiking',
  'Photography', 'Adventure', 'Relaxation', 'Cultural sites', 'Local markets'
];

const GOOGLE_API_KEY = 'YOUR_GOOGLE_MAPS_API_KEY';

function App() {
  const [preferences, setPreferences] = useState({ 
    destination: '', 
    travel_dates: [], 
    interests: [], 
    radius: 50 
  });
  const [dateRange, setDateRange] = useState({
    startDate: '',
    endDate: ''
  }); 
  const [itinerary, setItinerary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [viewState, setViewState] = useState({
    latitude: 48.8566,
    longitude: 2.3522,
    zoom: 4
  });
  const [nearbyCities, setNearbyCities] = useState([]);
  const [userCoords, setUserCoords] = useState(null);
  const [selectedDay, setSelectedDay] = useState(null);
  const [weather, setWeather] = useState(null);

  const handleMapClick = useCallback((event) => {
    const { lngLat } = event;
    setPreferences(prev => ({
      ...prev,
      destination: `Lat: ${lngLat.lat.toFixed(4)}, Lng: ${lngLat.lng.toFixed(4)}`
    }));
  }, []);

  const toggleInterest = (interest) => {
    const interests = preferences.interests.includes(interest)
      ? preferences.interests.filter(i => i !== interest)
      : [...preferences.interests, interest];
    setPreferences({ ...preferences, interests });
  };

  const generateDatesFromRange = (startDate, endDate) => {
    if (!startDate || !endDate) return [];
    
    const dates = [];
    const start = new Date(startDate);
    const end = new Date(endDate);
    
    if (start > end) return [];
    
    const currentDate = new Date(start);
    while (currentDate <= end) {
      dates.push(currentDate.toISOString().split('T')[0]);
      currentDate.setDate(currentDate.getDate() + 1);
    }
    
    return dates;
  };


  const handleDateRangeChange = (field, value) => {
    const newDateRange = { ...dateRange, [field]: value };
    setDateRange(newDateRange);
    
    const travelDates = generateDatesFromRange(
      field === 'startDate' ? value : dateRange.startDate,
      field === 'endDate' ? value : dateRange.endDate
    );
    
    setPreferences(prev => ({
      ...prev,
      travel_dates: travelDates
    }));
  };

  const formatDateDisplay = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { 
      weekday: 'short', 
      month: 'short', 
      day: 'numeric',
      year: 'numeric'
    });
  };

  const formatDateRange = () => {
    if (!dateRange.startDate || !dateRange.endDate) return '';
    
    const start = new Date(dateRange.startDate);
    const end = new Date(dateRange.endDate);
    const nights = Math.ceil((end - start) / (1000 * 60 * 60 * 24));
    
    return `${formatDateDisplay(dateRange.startDate)} → ${formatDateDisplay(dateRange.endDate)} (${nights + 1} days)`;
  };

  const handleSubmit = async () => {
    if (preferences.travel_dates.length === 0) {
      setError('Please select your travel dates');
      return;
    }

    setLoading(true);
    setError(null);
    setItinerary(null);
    setWeather(null);

    try {
      const res = await fetch('http://localhost:8000/generate-itinerary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          destination: preferences.destination,
          travel_dates: preferences.travel_dates,
          preferences: { interests: preferences.interests },
          radius: preferences.radius
        })
      });
      
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      
      const data = await res.json();
      setItinerary(data.plan || []);
      setNearbyCities(data.nearby_cities || []);
      setUserCoords(data.user_coordinates || null);
      setWeather(data.weather || null);
      
      console.log('API Response:', data);
    } catch (err) {
      console.error('API Error:', err);
      setError('Failed to generate itinerary. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const getWeatherIcon = (iconCode, description) => {
    if (description.toLowerCase().includes('rain') || description.toLowerCase().includes('drizzle')) {
      return <CloudRain size={20} color="#60a5fa" />;
    } else if (description.toLowerCase().includes('cloud')) {
      return <Cloud size={20} color="#9ca3af" />;
    } else {
      return <Sun size={20} color="#fbbf24" />;
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      weekday: 'short', 
      month: 'short', 
      day: 'numeric' 
    });
  };

  const getGoogleMapsLink = (dayRoute, startCoords) => {
    if (!dayRoute || dayRoute.length === 0) return '#';
    
    const [startLat, startLng] = startCoords;
    
    if (dayRoute.length === 1) {
      const destination = dayRoute[0];
      return `https://www.google.com/maps/dir/?api=1&origin=${startLat},${startLng}&destination=${destination.lat},${destination.lng}&key=${GOOGLE_API_KEY}`;
    }
    
    const destination = dayRoute[dayRoute.length - 1];
    const waypoints = dayRoute.slice(0, -1).map(p => `${p.lat},${p.lng}`).join('|');
    
    return `https://www.google.com/maps/dir/?api=1&origin=${startLat},${startLng}&destination=${destination.lat},${destination.lng}&waypoints=${waypoints}&key=${GOOGLE_API_KEY}`;
  };

  const getStartingCoordinates = () => {
    if (!preferences.destination) return [0, 0];
    const match = preferences.destination.match(/Lat:\s*([0-9\.-]+),\s*Lng:\s*([0-9\.-]+)/);
    return match ? [parseFloat(match[1]), parseFloat(match[2])] : [0, 0];
  };

  const getTotalTravelDistance = () => {
    if (!Array.isArray(itinerary)) return 0;
    return itinerary.reduce((total, day) => total + (day.travel_distance_km || 0), 0);
  };


  const getTodayDate = () => {
    const today = new Date();
    return today.toISOString().split('T')[0];
  };

 
  const isValidDateRange = () => {
    if (!dateRange.startDate || !dateRange.endDate) return false;
    const start = new Date(dateRange.startDate);
    const end = new Date(dateRange.endDate);
    return start <= end;
  };

  const styles = {
    container: {
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #1f2937 0%, #111827 50%, #000000 100%)',
      color: '#f9fafb',
      fontFamily: 'system-ui, -apple-system, sans-serif'
    },
    header: {
      background: 'rgba(17, 24, 39, 0.8)',
      backdropFilter: 'blur(10px)',
      borderBottom: '1px solid rgba(75, 85, 99, 0.3)',
      padding: '1rem 2rem',
      position: 'sticky',
      top: 0,
      zIndex: 50
    },
    headerContent: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      maxWidth: '1200px',
      margin: '0 auto'
    },
    logo: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem'
    },
    logoIcon: {
      width: '40px',
      height: '40px',
      background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
      borderRadius: '12px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    },
    main: {
      maxWidth: '1400px',
      margin: '0 auto',
      padding: '2rem'
    },
    hero: {
      textAlign: 'center',
      marginBottom: '3rem'
    },
    heroTitle: {
      fontSize: '2.5rem',
      fontWeight: 'bold',
      background: 'linear-gradient(135deg, #60a5fa, #a78bfa)',
      WebkitBackgroundClip: 'text',
      WebkitTextFillColor: 'transparent',
      marginBottom: '1rem'
    },
    heroSubtitle: {
      fontSize: '1.25rem',
      color: '#d1d5db',
      maxWidth: '600px',
      margin: '0 auto'
    },
    grid: {
      display: 'grid',
      gridTemplateColumns: '1fr 2fr',
      gap: '2rem',
      alignItems: 'start'
    },
    card: {
      background: 'rgba(31, 41, 55, 0.6)',
      backdropFilter: 'blur(10px)',
      border: '1px solid rgba(75, 85, 99, 0.3)',
      borderRadius: '24px',
      padding: '1.5rem',
      boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)'
    },
    cardTitle: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
      fontSize: '1.25rem',
      fontWeight: '600',
      marginBottom: '1.5rem'
    },
    titleIcon: {
      width: '32px',
      height: '32px',
      background: 'linear-gradient(135deg, #3b82f6, #06b6d4)',
      borderRadius: '8px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    },
    formGroup: {
      marginBottom: '1.5rem'
    },
    label: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      fontSize: '0.875rem',
      fontWeight: '500',
      marginBottom: '0.75rem',
      color: '#e5e7eb'
    },
    mapContainer: {
      position: 'relative',
      borderRadius: '16px',
      overflow: 'hidden',
      border: '2px solid transparent',
      transition: 'border-color 0.3s ease'
    },
    mapBadge: {
      position: 'absolute',
      top: '12px',
      left: '12px',
      background: 'linear-gradient(135deg, #10b981, #059669)',
      color: 'white',
      padding: '0.5rem 0.75rem',
      borderRadius: '20px',
      fontSize: '0.75rem',
      fontWeight: '500',
      zIndex: 10
    },
    dateRangeContainer: {
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      gap: '0.75rem',
      marginBottom: '0.75rem'
    },
    dateInput: {
      padding: '0.75rem 1rem',
      background: 'rgba(55, 65, 81, 0.6)',
      border: '1px solid rgba(107, 114, 128, 0.3)',
      borderRadius: '12px',
      color: '#f9fafb',
      fontSize: '0.875rem'
    },
    dateRangeDisplay: {
      background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(139, 92, 246, 0.1))',
      border: '1px solid rgba(59, 130, 246, 0.2)',
      borderRadius: '16px',
      padding: '1rem',
      marginTop: '0.75rem'
    },
    dateRangeInfo: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      marginBottom: '0.5rem'
    },
    dateRangeText: {
      color: '#93c5fd',
      fontSize: '0.875rem',
      fontWeight: '500'
    },
    dateCount: {
      background: 'rgba(59, 130, 246, 0.2)',
      color: '#60a5fa',
      padding: '0.25rem 0.75rem',
      borderRadius: '12px',
      fontSize: '0.75rem',
      fontWeight: '600'
    },
    selectedDatesPreview: {
      display: 'flex',
      flexWrap: 'wrap',
      gap: '0.25rem',
      marginTop: '0.5rem'
    },
    datePreviewTag: {
      background: 'rgba(59, 130, 246, 0.3)',
      color: '#93c5fd',
      padding: '0.25rem 0.5rem',
      borderRadius: '8px',
      fontSize: '0.75rem'
    },
    rangeContainer: {
      position: 'relative'
    },
    range: {
      width: '100%',
      height: '8px',
      background: 'rgba(55, 65, 81, 0.6)',
      borderRadius: '4px',
      outline: 'none',
      cursor: 'pointer'
    },
    rangeLabels: {
      display: 'flex',
      justifyContent: 'space-between',
      fontSize: '0.75rem',
      color: '#9ca3af',
      marginTop: '0.5rem'
    },
    interestsGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(3, 1fr)',
      gap: '0.5rem'
    },
    interestButton: {
      padding: '0.75rem',
      borderRadius: '12px',
      border: 'none',
      fontSize: '0.875rem',
      fontWeight: '500',
      cursor: 'pointer',
      transition: 'all 0.2s ease',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    },
    interestSelected: {
      background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
      color: 'white',
      transform: 'scale(1.05)'
    },
    interestUnselected: {
      background: 'rgba(55, 65, 81, 0.4)',
      color: '#d1d5db'
    },
    generateButton: {
      width: '100%',
      padding: '1rem 2rem',
      background: 'linear-gradient(135deg, #2563eb, #7c3aed)',
      color: 'white',
      border: 'none',
      borderRadius: '16px',
      fontSize: '1rem',
      fontWeight: '600',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '0.75rem',
      transition: 'all 0.3s ease',
      boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)'
    },
    weatherCard: {
      background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(6, 182, 212, 0.1))',
      border: '1px solid rgba(16, 185, 129, 0.2)',
      borderRadius: '20px',
      padding: '1.5rem',
      marginBottom: '1.5rem'
    },
    weatherHeader: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      marginBottom: '1rem'
    },
    weatherCurrent: {
      display: 'flex',
      alignItems: 'center',
      gap: '1rem',
      marginBottom: '1rem'
    },
    temperatureDisplay: {
      fontSize: '2rem',
      fontWeight: 'bold',
      color: '#10b981'
    },
    weatherDetails: {
      display: 'grid',
      gridTemplateColumns: 'repeat(3, 1fr)',
      gap: '1rem',
      marginBottom: '1.5rem'
    },
    weatherDetailItem: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      fontSize: '0.875rem',
      color: '#d1d5db'
    },
    forecastGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
      gap: '0.75rem'
    },
    forecastItem: {
      background: 'rgba(31, 41, 55, 0.4)',
      borderRadius: '12px',
      padding: '0.75rem',
      textAlign: 'center',
      fontSize: '0.75rem'
    },
    forecastDate: {
      color: '#9ca3af',
      marginBottom: '0.5rem'
    },
    forecastTemp: {
      fontWeight: 'bold',
      color: '#f9fafb',
      marginTop: '0.5rem'
    },
    dayCard: {
      background: 'rgba(31, 41, 55, 0.6)',
      backdropFilter: 'blur(10px)',
      border: '1px solid rgba(75, 85, 99, 0.3)',
      borderRadius: '20px',
      padding: '1.5rem',
      marginBottom: '1rem',
      cursor: 'pointer',
      transition: 'all 0.3s ease'
    },
    dayHeader: {
      display: 'flex',
      alignItems: 'center',
      gap: '1rem',
      marginBottom: '1rem'
    },
    dayNumber: {
      width: '48px',
      height: '48px',
      background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
      borderRadius: '16px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: 'white',
      fontSize: '1.25rem',
      fontWeight: 'bold'
    },
    dayInfo: {
      flex: 1
    },
    dayTitle: {
      fontSize: '1.25rem',
      fontWeight: 'bold',
      color: '#f9fafb',
      marginBottom: '0.25rem'
    },
    daySubtitle: {
      fontSize: '1rem',
      color: '#60a5fa',
      fontWeight: '500'
    },
    dayDate: {
      fontSize: '0.875rem',
      color: '#10b981',
      fontWeight: '500',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      marginBottom: '0.25rem'
    },
    distanceInfo: {
      display: 'flex',
      gap: '1rem',
      marginBottom: '1rem',
      flexWrap: 'wrap'
    },
    distanceBadge: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      background: 'rgba(55, 65, 81, 0.4)',
      padding: '0.5rem 0.75rem',
      borderRadius: '20px',
      fontSize: '0.875rem',
      color: '#d1d5db'
    },
    activities: {
      paddingLeft: '1rem'
    },
    activity: {
      display: 'flex',
      alignItems: 'flex-start',
      gap: '0.75rem',
      marginBottom: '0.75rem',
      color: '#e5e7eb'
    },
    activityDot: {
      width: '8px',
      height: '8px',
      background: 'linear-gradient(135deg, #60a5fa, #a78bfa)',
      borderRadius: '50%',
      marginTop: '0.5rem',
      flexShrink: 0
    },
    summaryCard: {
      background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(139, 92, 246, 0.1))',
      border: '1px solid rgba(59, 130, 246, 0.2)',
      borderRadius: '20px',
      padding: '1.5rem',
      marginBottom: '1.5rem'
    },
    summaryGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(4, 1fr)',
      gap: '1rem',
      marginTop: '1rem'
    },
    summaryItem: {
      textAlign: 'center'
    },
    summaryNumber: {
      fontSize: '1.5rem',
      fontWeight: 'bold',
      marginBottom: '0.25rem'
    },
    summaryLabel: {
      fontSize: '0.875rem',
      color: '#d1d5db'
    },
    loadingCard: {
      background: 'rgba(31, 41, 55, 0.6)',
      backdropFilter: 'blur(10px)',
      border: '1px solid rgba(75, 85, 99, 0.3)',
      borderRadius: '20px',
      padding: '3rem',
      textAlign: 'center'
    },
    errorCard: {
      background: 'rgba(239, 68, 68, 0.1)',
      border: '1px solid rgba(239, 68, 68, 0.2)',
      borderRadius: '16px',
      padding: '1.5rem',
      marginBottom: '1.5rem'
    },
    mapsLink: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: '0.5rem',
      background: 'linear-gradient(135deg, #2563eb, #7c3aed)',
      color: 'white',
      padding: '0.75rem 1.5rem',
      borderRadius: '12px',
      textDecoration: 'none',
      fontSize: '0.875rem',
      fontWeight: '500',
      marginTop: '1rem',
      transition: 'all 0.3s ease'
    },
    weatherWarning: {
      background: 'rgba(245, 158, 11, 0.1)',
      border: '1px solid rgba(245, 158, 11, 0.3)',
      borderRadius: '12px',
      padding: '0.75rem',
      marginBottom: '1rem',
      fontSize: '0.875rem',
      color: '#fbbf24'
    }
  };

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <div style={styles.headerContent}>
          <div style={styles.logo}>
            <div style={styles.logoIcon}>
              <Globe size={24} color="white" />
            </div>
            <div>
              <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', margin: 0 }}>TravelAI</h1>
              <p style={{ fontSize: '0.875rem', color: '#9ca3af', margin: 0 }}>Date Range Trip Planner</p>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.875rem', color: '#9ca3af' }}>
            <div style={{ width: '8px', height: '8px', background: '#10b981', borderRadius: '50%' }}></div>
            <span>Online</span>
          </div>
        </div>
      </header>

      <main style={styles.main}>
        <div style={styles.hero}>
          <h2 style={styles.heroTitle}>Plan Your Perfect Journey</h2>
          <p style={styles.heroSubtitle}>
            Select your travel date range and discover personalized itineraries powered by AI, with weather forecasts for your entire trip.
          </p>
        </div>

        <div style={styles.grid}>
          <div>
            <div style={styles.card}>
              <div style={styles.cardTitle}>
                <div style={styles.titleIcon}>
                  <Target size={20} color="white" />
                </div>
                Trip Configuration
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>
                  <MapPin size={16} color="#60a5fa" />
                  Choose Your Destination
                </label>
                <div style={styles.mapContainer}>
                  <Map
                    initialViewState={viewState}
                    style={{ height: 200 }}
                    mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
                    onMove={evt => setViewState(evt.viewState)}
                    onClick={handleMapClick}
                  />
                  {preferences.destination && (
                    <div style={styles.mapBadge}>
                      📍 Location Selected
                    </div>
                  )}
                </div>
                {preferences.destination && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.75rem', fontSize: '0.875rem' }}>
                    <CheckCircle size={16} color="#10b981" />
                    <span style={{ color: '#d1d5db' }}>Coordinates: </span>
                    <span style={{ color: '#10b981', fontFamily: 'monospace' }}>
                      {preferences.destination.replace('Lat: ', '').replace('Lng: ', '')}
                    </span>
                  </div>
                )}
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>
                  <CalendarRange size={16} color="#a78bfa" />
                  Select Travel Date Range
                </label>
                <div style={styles.dateRangeContainer}>
                  <div>
                    <label style={{ fontSize: '0.75rem', color: '#9ca3af', marginBottom: '0.25rem', display: 'block' }}>
                      From
                    </label>
                    <input
                      type="date"
                      value={dateRange.startDate}
                      onChange={(e) => handleDateRangeChange('startDate', e.target.value)}
                      min={getTodayDate()}
                      style={styles.dateInput}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: '0.75rem', color: '#9ca3af', marginBottom: '0.25rem', display: 'block' }}>
                      To
                    </label>
                    <input
                      type="date"
                      value={dateRange.endDate}
                      onChange={(e) => handleDateRangeChange('endDate', e.target.value)}
                      min={dateRange.startDate || getTodayDate()}
                      style={styles.dateInput}
                    />
                  </div>
                </div>
                
                {isValidDateRange() && preferences.travel_dates.length > 0 && (
                  <div style={styles.dateRangeDisplay}>
                    <div style={styles.dateRangeInfo}>
                      <div style={styles.dateRangeText}>
                        <CalendarDays size={14} style={{ display: 'inline', marginRight: '0.5rem' }} />
                        {formatDateRange()}
                      </div>
                      <div style={styles.dateCount}>
                        {preferences.travel_dates.length} days
                      </div>
                    </div>
                    <div style={styles.selectedDatesPreview}>
                      {preferences.travel_dates.slice(0, 7).map((date, index) => (
                        <div key={index} style={styles.datePreviewTag}>
                          {formatDate(date)}
                        </div>
                      ))}
                      {preferences.travel_dates.length > 7 && (
                        <div style={styles.datePreviewTag}>
                          +{preferences.travel_dates.length - 7} more
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>
                  <Route size={16} color="#f59e0b" />
                  Radius: {preferences.radius}km
                </label>
                <div style={styles.rangeContainer}>
                  <input
                    type="range"
                    min="10"
                    max="200"
                    value={preferences.radius}
                    onChange={e => setPreferences({ ...preferences, radius: parseInt(e.target.value) })}
                    style={styles.range}
                  />
                  <div style={styles.rangeLabels}>
                    <span>10km</span>
                    <span>200km</span>
                  </div>
                </div>
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>
                  <Star size={16} color="#fbbf24" />
                  Your Interests ({preferences.interests.length} selected)
                </label>
                <div style={styles.interestsGrid}>
                  {INTEREST_OPTIONS.map(interest => (
                    <button
                      key={interest}
                      onClick={() => toggleInterest(interest)}
                      style={{
                        ...styles.interestButton,
                        ...(preferences.interests.includes(interest) 
                          ? styles.interestSelected 
                          : styles.interestUnselected
                        )
                      }}
                    >
                      {interest}
                    </button>
                  ))}
                </div>
              </div>

              <button
                onClick={handleSubmit}
                disabled={loading || !preferences.destination || preferences.travel_dates.length === 0}
                style={{
                  ...styles.generateButton,
                  opacity: (loading || !preferences.destination || preferences.travel_dates.length === 0) ? 0.6 : 1,
                  cursor: (loading || !preferences.destination || preferences.travel_dates.length === 0) ? 'not-allowed' : 'pointer'
                }}
              >
                {loading ? (
                  <React.Fragment>
                    <Loader2 size={20} className="animate-spin" />
                    <span>Creating Your Journey...</span>
                  </React.Fragment>
                ) : (
                  <React.Fragment>
                    <Globe size={20} />
                    <span>Generate Perfect Itinerary</span>
                  </React.Fragment>
                )}
              </button>
            </div>
          </div>

          <div>
            {error && (
              <div style={styles.errorCard}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <AlertCircle size={24} color="#ef4444" />
                  <div>
                    <h3 style={{ color: '#fca5a5', margin: '0 0 0.25rem 0', fontWeight: '500' }}>Something went wrong</h3>
                    <p style={{ color: '#fecaca', margin: 0, fontSize: '0.875rem' }}>{error}</p>
                  </div>
                </div>
              </div>
            )}

            {loading && (
              <div style={styles.loadingCard}>
                <Loader2 size={48} color="#60a5fa" className="animate-spin" style={{ margin: '0 auto 1.5rem' }} />
                <h3 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '0.5rem' }}>Crafting Your Perfect Itinerary</h3>
                <p style={{ color: '#d1d5db' }}>Our AI is analyzing your preferences and finding the best experiences for your selected dates...</p>
              </div>
            )}

            {/* Weather Display - Only show for specific dates */}
            {weather && (
              <div style={styles.weatherCard}>
                <div style={styles.weatherHeader}>
                  <h3 style={{ 
                    fontSize: '1.25rem', 
                    fontWeight: '600', 
                    margin: 0,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem'
                  }}>
                    <Cloud size={20} color="#10b981" />
                    Weather Forecast for Your Trip
                  </h3>
                  <span style={{ fontSize: '0.875rem', color: '#9ca3af' }}>
                    {weather.location} {weather.country && `• ${weather.country}`}
                  </span>
                </div>

                {weather.missing_dates && weather.missing_dates.length > 0 && (
                  <div style={styles.weatherWarning}>
                    <AlertCircle size={16} style={{ display: 'inline', marginRight: '0.5rem' }} />
                    Weather forecast not available for: {weather.missing_dates.join(', ')}
                  </div>
                )}

                {weather.current && (
                  <div style={styles.weatherCurrent}>
                    <div>
                      <div style={styles.temperatureDisplay}>
                        {weather.current.temperature}°C
                      </div>
                      <div style={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        gap: '0.5rem',
                        color: '#d1d5db' 
                      }}>
                        {getWeatherIcon(weather.current.icon, weather.current.description)}
                        <span>{weather.current.description}</span>
                      </div>
                    </div>
                  </div>
                )}

                {weather.current && (
                  <div style={styles.weatherDetails}>
                    <div style={styles.weatherDetailItem}>
                      <Thermometer size={16} color="#60a5fa" />
                      <span>Feels like {weather.current.feels_like}°C</span>
                    </div>
                    <div style={styles.weatherDetailItem}>
                      <Droplets size={16} color="#06b6d4" />
                      <span>{weather.current.humidity}% humidity</span>
                    </div>
                    <div style={styles.weatherDetailItem}>
                      <Wind size={16} color="#9ca3af" />
                      <span>{weather.current.wind_speed} km/h wind</span>
                    </div>
                  </div>
                )}

                {weather.forecast && weather.forecast.length > 0 && (
                  <div>
                    <h4 style={{ 
                      fontSize: '1rem', 
                      fontWeight: '500', 
                      margin: '0 0 0.75rem 0',
                      color: '#e5e7eb'
                    }}>
                      Forecast for Your Travel Days
                    </h4>
                    <div style={styles.forecastGrid}>
                      {weather.forecast.map((day, idx) => (
                        <div key={idx} style={styles.forecastItem}>
                          <div style={styles.forecastDate}>
                            Day {day.travel_day}: {formatDate(day.date)}
                          </div>
                          <div style={{ margin: '0.5rem 0' }}>
                            {getWeatherIcon(day.icon, day.description)}
                          </div>
                          <div style={{ 
                            fontSize: '0.75rem', 
                            color: '#9ca3af',
                            marginBottom: '0.25rem'
                          }}>
                            {day.description}
                          </div>
                          <div style={styles.forecastTemp}>
                            {day.temperature_max}° / {day.temperature_min}°
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {Array.isArray(itinerary) && itinerary.length > 0 && (
              <div>
                {nearbyCities && nearbyCities.length > 0 && (
                  <div style={{
                    background: 'rgba(59, 130, 246, 0.1)',
                    border: '1px solid rgba(59, 130, 246, 0.2)',
                    borderRadius: '16px',
                    padding: '1rem',
                    marginBottom: '1.5rem'
                  }}>
                    <h3 style={{ 
                      fontSize: '1rem', 
                      fontWeight: '600', 
                      margin: '0 0 0.75rem 0',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem'
                    }}>
                      <MapPin size={16} color="#60a5fa" />
                      Nearby Cities Found ({nearbyCities.length})
                    </h3>
                    <div style={{ 
                      display: 'flex', 
                      flexWrap: 'wrap', 
                      gap: '0.5rem' 
                    }}>
                      {nearbyCities.map((city, idx) => (
                        <span key={idx} style={{
                          background: 'rgba(59, 130, 246, 0.2)',
                          color: '#93c5fd',
                          padding: '0.25rem 0.75rem',
                          borderRadius: '12px',
                          fontSize: '0.875rem'
                        }}>
                          {city}
                        </span>
                      ))}
                    </div>
                    {userCoords && (
                      <p style={{ 
                        margin: '0.75rem 0 0 0', 
                        fontSize: '0.75rem', 
                        color: '#9ca3af',
                        fontFamily: 'monospace'
                      }}>
                        Search center: {userCoords.lat.toFixed(4)}, {userCoords.lng.toFixed(4)}
                      </p>
                    )}
                  </div>
                )}

                <div style={styles.summaryCard}>
                  <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', margin: '0 0 1rem 0', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <Calendar size={24} color="#60a5fa" />
                    Your Personalized Journey
                  </h2>
                  <div style={styles.summaryGrid}>
                    <div style={styles.summaryItem}>
                      <div style={{ ...styles.summaryNumber, color: '#60a5fa' }}>{preferences.travel_dates.length}</div>
                      <div style={styles.summaryLabel}>Travel Days</div>
                    </div>
                    <div style={styles.summaryItem}>
                      <div style={{ ...styles.summaryNumber, color: '#a78bfa' }}>{preferences.interests.length}</div>
                      <div style={styles.summaryLabel}>Interests</div>
                    </div>
                    <div style={styles.summaryItem}>
                      <div style={{ ...styles.summaryNumber, color: '#10b981' }}>{preferences.radius}km</div>
                      <div style={styles.summaryLabel}>Radius</div>
                    </div>
                    <div style={styles.summaryItem}>
                      <div style={{ ...styles.summaryNumber, color: '#f59e0b' }}>{getTotalTravelDistance().toFixed(1)}km</div>
                      <div style={styles.summaryLabel}>Total Travel</div>
                    </div>
                  </div>
                </div>

                {itinerary.map((day, i) => (
                  <div
                    key={i}
                    onClick={() => setSelectedDay(selectedDay === i ? null : i)}
                    style={{
                      ...styles.dayCard,
                      ...(selectedDay === i ? { 
                        border: '2px solid #60a5fa', 
                        transform: 'translateY(-4px)',
                        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.2)'
                      } : {})
                    }}
                  >
                    <div style={styles.dayHeader}>
                      <div style={styles.dayNumber}>{day.day}</div>
                      <div style={styles.dayInfo}>
                        {day.date && (
                          <div style={styles.dayDate}>
                            <Calendar size={14} />
                            {day.formatted_date || formatDateDisplay(day.date)}
                          </div>
                        )}
                        <h3 style={styles.dayTitle}>{day.town}</h3>
                        <h4 style={styles.daySubtitle}>{day.place}</h4>
                      </div>
                      <Clock size={20} color="#9ca3af" />
                    </div>

                    <div style={styles.distanceInfo}>
                      <div style={styles.distanceBadge}>
                        <MapPin size={16} color="#60a5fa" />
                        <span>{day.distance_from_start}km from start</span>
                      </div>
                      {day.travel_distance_km !== undefined && day.travel_distance_km > 0 && (
                        <div style={styles.distanceBadge}>
                          <Route size={16} color="#10b981" />
                          <span>{day.travel_distance_km}km travel</span>
                        </div>
                      )}
                    </div>

                    <div style={styles.activities}>
                      {day.activities.map((activity, idx) => (
                        <div key={idx} style={styles.activity}>
                          <div style={styles.activityDot}></div>
                          <span>{activity}</span>
                        </div>
                      ))}
                    </div>

                    {selectedDay === i && day.route && (
                      <a
                        href={getGoogleMapsLink(day.route, getStartingCoordinates())}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={styles.mapsLink}
                      >
                        <ExternalLink size={16} />
                        View Route on Google Maps
                      </a>
                    )}
                  </div>
                ))}
              </div>
            )}

            {itinerary && Array.isArray(itinerary) && itinerary.length === 0 && (
              <div style={{
                background: 'rgba(245, 158, 11, 0.1)',
                border: '1px solid rgba(245, 158, 11, 0.2)',
                borderRadius: '20px',
                padding: '3rem',
                textAlign: 'center'
              }}>
                <AlertCircle size={48} color="#f59e0b" style={{ margin: '0 auto 1.5rem' }} />
                <h3 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '1rem' }}>No Destinations Found</h3>
                <p style={{ color: '#d1d5db', fontSize: '1.125rem' }}>
                  Try adjusting your preferences, selecting a different location, or increasing the travel radius to discover more options.
                </p>
              </div>
            )}

            {!itinerary && !loading && !error && (
              <div style={styles.loadingCard}>
                <div style={{ 
                  width: '80px', 
                  height: '80px', 
                  background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)', 
                  borderRadius: '50%', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  margin: '0 auto 1.5rem'
                }}>
                  <CalendarRange size={40} color="white" />
                </div>
                <h3 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '0.75rem' }}>Ready for Your Next Adventure?</h3>
                <p style={{ color: '#d1d5db', maxWidth: '400px', margin: '0 auto' }}>
                  Click on the map to select your destination, choose your travel date range, and let our AI create the perfect itinerary with weather forecasts.
                </p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
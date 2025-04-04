import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Paper, Grid, Button,
  Slider, FormControlLabel, Switch, Typography, FormControl,
  InputLabel, Select, MenuItem, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Chip, Divider,
  CircularProgress, Alert, Tooltip, IconButton, Collapse, List, ListItem, ListItemText, TextField
} from '@mui/material';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import ReplayIcon from '@mui/icons-material/Replay';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import BugReportIcon from '@mui/icons-material/BugReport';
import ArrowUpward from '@mui/icons-material/ArrowUpward';
import ArrowDownward from '@mui/icons-material/ArrowDownward';
import SearchIcon from '@mui/icons-material/Search';
import { experimentService, API_URL as DEFAULT_API_URL } from '../services/api';
import { List as ListIcon } from '@mui/icons-material';
import LaunchIcon from '@mui/icons-material/Launch';
import { TransformedQuery } from './TransformedQuery';

/**
 * Component for experimenting with different boost factors and their impact on ranking
 * 
 * @param {Object} props - Component props
 * @param {Array} props.originalResults - The original search results to re-rank
 * @param {string} props.query - The search query used to retrieve results
 * @param {function} props.onRunNewSearch - Callback function when user wants to run a new search
 * @param {Object} props.results - Full search results including Google Scholar for comparison
 */
const BoostExperiment = ({ originalResults, query, API_URL = DEFAULT_API_URL, onRunNewSearch, results }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [boostedResults, setBoostedResults] = useState(null);
  const [debugMode, setDebugMode] = useState(false);
  const [debugInfo, setDebugInfo] = useState(null);
  const [searchLoading, setSearchLoading] = useState(false);
  const [transformedQuery, setTransformedQuery] = useState(null);
  
  // State for boost configuration
  const [boostConfig, setBoostConfig] = useState({
    enableFieldBoosts: true,
    fieldBoosts: {
      title: 0.0,  // Set default to 0
      abstract: 0.0,
      authors: 0.0,
      year: 0.0,
    },
    citationBoost: 0.0,  // Set default to 0
    recencyBoost: 0.0,  // Set default to 0
    referenceYear: new Date().getFullYear(),
    doctypeBoosts: {
      journal: 0.0,  // Set default to 0
      conference: 0.0,
      book: 0.0,
      thesis: 0.0,
    }
  });
  
  // Function to handle boost changes
  const handleBoostChange = (type, field, value) => {
    setBoostConfig(prev => {
      if (type === 'fieldBoosts' || type === 'doctypeBoosts') {
        return {
          ...prev,
          [type]: {
            ...prev[type],
            [field]: value
          }
        };
      }
      return {
        ...prev,
        [type]: value
      };
    });
  };
  
  // Function to transform the query based on the field boosts
  const transformQuery = useCallback((originalQuery) => {
    if (!boostConfig.enableFieldBoosts) {
      return originalQuery;
    }
    
    // Clean the original query - important to strip any existing field boosts
    let cleanQuery = originalQuery.trim();
    
    // If the query already has field boosts, extract the base query
    // This prevents nesting of field boosts when applying changes multiple times
    if (cleanQuery.includes("^") || cleanQuery.includes(":")) {
      // Try to extract the original search term
      const originalTermMatch = cleanQuery.match(/^[^:]*:([^"]*)["\^]/) || 
                               cleanQuery.match(/^[^:]*:"([^"]*)"/) ||
                               cleanQuery.match(/^([^:]+)$/);
      
      if (originalTermMatch && originalTermMatch[1]) {
        cleanQuery = originalTermMatch[1].trim();
        console.log("Extracted original query term:", cleanQuery);
      } else {
        // If we can't extract the original term, use the original query from props
        cleanQuery = query;
        console.log("Using original prop query:", cleanQuery);
      }
    }
    
    if (!cleanQuery) return "";
    
    console.log("Transforming query:", cleanQuery, "with config:", boostConfig);
    
    // Sort fields by boost value in descending order
    const sortedFields = Object.entries(boostConfig.fieldBoosts)
      .filter(([_, boost]) => boost !== '' && boost !== null && boost !== undefined && boost > 0)
      .sort(([_, a], [__, b]) => parseFloat(b) - parseFloat(a))
      .map(([field]) => field);
    
    if (sortedFields.length === 0) {
      return cleanQuery;
    }
    
    const parts = [];
    
    // Process each field in order of highest boost first
    for (const field of sortedFields) {
      const boost = parseFloat(boostConfig.fieldBoosts[field]).toFixed(1);
      
      // Split query into terms and phrases
      const terms = [];
      const phrases = [];
      let currentTerm = [];
      let inPhrase = false;
      
      // Split the query into terms and phrases
      const words = cleanQuery.split(/\s+/);
      for (let i = 0; i < words.length; i++) {
        const word = words[i];
        
        if (word.startsWith('"')) {
          inPhrase = true;
          currentTerm = [word.slice(1)];
        } else if (word.endsWith('"')) {
          inPhrase = false;
          currentTerm.push(word.slice(0, -1));
          phrases.push(currentTerm.join(' '));
          currentTerm = [];
        } else if (inPhrase) {
          currentTerm.push(word);
        } else {
          terms.push(word);
        }
      }
      
      // Add single terms
      for (const term of terms) {
        parts.push(`${field}:${term}^${boost}`);
      }
      
      // Add phrases
      for (const phrase of phrases) {
        parts.push(`${field}:"${phrase}"^${boost}`);
      }
      
      // Generate combinations of non-phrase terms if we have at least 2
      if (terms.length >= 2) {
        // Generate combinations of size 2 to n
        for (let size = 2; size <= terms.length; size++) {
          const combinations = getCombinations(terms, size);
          for (const combo of combinations) {
            parts.push(`${field}:"${combo.join(' ')}"^${boost}`);
          }
        }
      }
      
      // Handle mixed terms and phrases
      if (terms.length > 0 && phrases.length > 0) {
        for (const phrase of phrases) {
          for (const term of terms) {
            parts.push(`${field}:"${phrase} ${term}"^${boost}`);
            parts.push(`${field}:"${term} ${phrase}"^${boost}`);
          }
        }
      }
    }
    
    // Join all parts with OR operators
    const result = parts.join(" OR ");
    console.log("Final transformed query:", result);
    return result;
  }, [boostConfig, query]);
  
  // Helper function to generate combinations
  const getCombinations = (arr, size) => {
    const result = [];
    
    function combine(start, current) {
      if (current.length === size) {
        result.push([...current]);
        return;
      }
      
      for (let i = start; i < arr.length; i++) {
        current.push(arr[i]);
        combine(i + 1, current);
        current.pop();
      }
    }
    
    combine(0, []);
    return result;
  };
  
  // Debug logging
  useEffect(() => {
    console.log('BoostExperiment mounted with:', {
      originalResultsLength: originalResults?.length,
      query,
      boostConfig
    });
    
    // Log the transformed query for debugging
    if (query) {
      const transformedQuery = transformQuery(query);
      console.log('Transformed query:', transformedQuery);
    }
    
    if (originalResults?.length > 0) {
      // COMPREHENSIVE LOGGING: Log the entire first result to see the complete structure
      console.log("CRITICAL: Complete structure of first result:", JSON.stringify(originalResults[0], null, 2));
      
      // Log much more detailed information about the original search results
      const yearTypes = originalResults.map(r => typeof r.year).filter((v, i, a) => a.indexOf(v) === i);
      const sampleYears = originalResults.slice(0, 5).map(r => r.year);
      const hasArrayYears = originalResults.some(r => Array.isArray(r.year));
      const yearStructure = {
        types_present: yearTypes,
        sample_values: sampleYears,
        any_arrays: hasArrayYears,
        original_display: originalResults.slice(0, 5).map(r => ({
          title: truncateText(r.title, 30),
          year_display: r.year,
          year_type: typeof r.year,
          year_json: JSON.stringify(r.year)
        }))
      };
      
      console.log("CRITICAL DEBUGGING - Years in original results:", yearStructure);
      
      // Check for alternative fields that might contain year information
      const alternativeFields = originalResults.slice(0, 3).map(r => ({
        title: truncateText(r.title, 30),
        pub_year: r.pub_year,
        date: r.date,
        pubdate: r.pubdate,
        publication_year: r.publication_year,
        year_of_publication: r.year_of_publication
      }));
      console.log("CHECKING ALTERNATIVE YEAR FIELDS:", alternativeFields);
      
      console.log("Sample result metadata:", {
        citation: originalResults[0].citation_count,
        year: originalResults[0].year,
        year_type: typeof originalResults[0].year,
        doctype: originalResults[0].doctype,
        properties: originalResults[0].property
      });
    }
  }, [originalResults, query, boostConfig]);
  
  // Helper functions for title comparison
  const normalizeTitle = (title) => {
    if (!title) return '';
    // Remove special characters, extra spaces, lowercase everything
    return title.toLowerCase()
      .replace(/[^\w\s]/g, '') // Remove special chars
      .replace(/\s+/g, ' ')    // Replace multiple spaces with single space
      .trim();
  };
  
  const calculateTitleSimilarity = (title1, title2) => {
    if (!title1 || !title2) return 0;
    
    const t1 = normalizeTitle(title1);
    const t2 = normalizeTitle(title2);
    
    // Simple Jaccard similarity for words
    const words1 = t1.split(' ');
    const words2 = t2.split(' ');
    
    const set1 = new Set(words1);
    const set2 = new Set(words2);
    
    const intersection = new Set([...set1].filter(x => set2.has(x)));
    const union = new Set([...set1, ...set2]);
    
    return intersection.size / union.size;
  };
  
  // Helper function to calculate rank changes with improved title matching
  const calculateRankChanges = useCallback((originalResults, boostedResults) => {
    console.log("Calculating rank changes with improved matching...");
    
    if (!originalResults || !boostedResults || 
        originalResults.length === 0 || boostedResults.length === 0) {
      console.warn("Missing results for comparison");
      return boostedResults;
    }
    
    // Create a map of original results for quick lookup
    const originalResultsMap = {};
    originalResults.forEach((result, index) => {
      if (result.title) {
        // Store by normalized title
        const normalizedTitle = normalizeTitle(result.title);
        originalResultsMap[normalizedTitle] = { result, index };
      }
      
      // Also store by bibcode if available
      if (result.bibcode) {
        originalResultsMap[result.bibcode] = { result, index };
      }
    });
    
    console.log(`Created mapping for ${Object.keys(originalResultsMap).length} original results`);
    
    // Process boosted results to add rank change information
    return boostedResults.map((result, newIndex) => {
      let originalData = null;
      
      // Try matching by bibcode first
      if (result.bibcode && originalResultsMap[result.bibcode]) {
        originalData = originalResultsMap[result.bibcode];
        console.log(`Match by bibcode for "${truncateText(result.title, 30)}"`);
      }
      
      // Then try normalized title
      if (!originalData && result.title) {
        const normalizedTitle = normalizeTitle(result.title);
        if (originalResultsMap[normalizedTitle]) {
          originalData = originalResultsMap[normalizedTitle];
          console.log(`Match by normalized title for "${truncateText(result.title, 30)}"`);
        }
      }
      
      // If still no match, try fuzzy title matching
      if (!originalData && result.title) {
        let bestMatchKey = null;
        let bestMatchScore = 0;
        
        // Check similarity with all original results
        Object.keys(originalResultsMap).forEach(key => {
          const original = originalResultsMap[key].result;
          if (original.title) {
            const score = calculateTitleSimilarity(result.title, original.title);
            if (score > 0.8 && score > bestMatchScore) {
              bestMatchScore = score;
              bestMatchKey = key;
            }
          }
        });
        
        if (bestMatchKey) {
          originalData = originalResultsMap[bestMatchKey];
          console.log(`Fuzzy match (${bestMatchScore.toFixed(2)}) for "${truncateText(result.title, 30)}"`);
        }
      }
      
      if (originalData) {
        const originalIndex = originalData.index;
        const rankChange = originalIndex - newIndex;
        
        return {
          ...result,
          originalRank: originalIndex + 1,
          rankChange: rankChange
        };
      } else {
        console.warn(`No match found for "${truncateText(result.title, 30)}"`);
        return {
          ...result,
          originalRank: null,
          rankChange: 0
        };
      }
    });
  }, []);
  
  // Function to handle running the boost experiment
  const handleRunBoostExperiment = async () => {
    setLoading(true);
    setError(null);
    try {
      // Transform the query
      const transformedQuery = transformQuery(query);
      
      // Make the API request
      const response = await fetch(`${API_URL}/api/search/compare`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: transformedQuery,
          originalQuery: query,
          sources: ['ads'],
          metrics: ['ndcg@10', 'precision@10', 'recall@10'],
          fields: ['title', 'abstract', 'authors', 'year', 'citation_count', 'doctype'],
          max_results: 20,
          useTransformedQuery: true,
          boost_config: {
            name: "Boosted Results",
            citation_boost: parseFloat(boostConfig.citationBoost),
            recency_boost: parseFloat(boostConfig.recencyBoost),
            reference_year: parseInt(boostConfig.referenceYear),
            doctype_boosts: Object.fromEntries(
              Object.entries(boostConfig.doctypeBoosts)
                .map(([key, value]) => [key, parseFloat(value)])
            )
          }
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to run boost experiment');
      }

      const data = await response.json();
      setBoostedResults(data);
      setTransformedQuery(transformedQuery);
    } catch (err) {
      console.error('Error running boost experiment:', err);
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };
  
  // Helper functions
  const truncateText = (text, maxLength) => {
    if (!text) return '';
    return text.length > maxLength ? `${text.substring(0, maxLength)}...` : text;
  };

  const formatAuthors = (authors) => {
    if (!authors) return 'Unknown';
    
    if (typeof authors === 'string') {
      return authors;
    }
    
    if (Array.isArray(authors)) {
      return authors.slice(0, 3).join(', ') + (authors.length > 3 ? ', et al.' : '');
    }
    
    return 'Unknown';
  };
  
  // Format rank change display
  const formatRankChange = (change) => {
    if (change > 0) {
      return (
        <Box sx={{ display: 'flex', alignItems: 'center', color: 'success.main' }}>
          <ArrowUpwardIcon fontSize="small" sx={{ mr: 0.5 }} />
          {change}
        </Box>
      );
    } else if (change < 0) {
      return (
        <Box sx={{ display: 'flex', alignItems: 'center', color: 'error.main' }}>
          <ArrowDownwardIcon fontSize="small" sx={{ mr: 0.5 }} />
          {Math.abs(change)}
        </Box>
      );
    } else {
      return '—';
    }
  };
  
  // Format boost factor display
  const formatBoostFactor = (value) => {
    if (value === undefined || value === null) return '—';
    return typeof value === 'number' ? value.toFixed(2) : String(value);
  };
  
  // Enhanced debug component to inspect fields and values
  const renderDebugPanel = () => {
    if (!debugInfo || !debugInfo.firstResult) return null;
    
    return (
      <Box sx={{ mt: 2, mb: 2, border: 1, borderColor: 'warning.light', p: 2, borderRadius: 1 }}>
        <Typography variant="h6" color="warning.main" gutterBottom>
          Debug Information
        </Typography>
        
        <Typography variant="subtitle2" gutterBottom>Metadata Fields (Required for Boosts)</Typography>
        <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Field Name</TableCell>
                <TableCell>Present</TableCell>
                <TableCell>Value</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              <TableRow>
                <TableCell>citation_count</TableCell>
                <TableCell>
                  {debugInfo.firstResult?.citation_count !== undefined ? (
                    <Chip label="Yes" size="small" color="success" />
                  ) : (
                    <Chip label="No" size="small" color="error" />
                  )}
                </TableCell>
                <TableCell>{debugInfo.firstResult?.citation_count !== undefined ? String(debugInfo.firstResult.citation_count) : 'N/A'}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>year</TableCell>
                <TableCell>
                  {debugInfo.firstResult?.year !== undefined ? (
                    <Chip label="Yes" size="small" color="success" />
                  ) : (
                    <Chip label="No" size="small" color="error" />
                  )}
                </TableCell>
                <TableCell>{debugInfo.firstResult?.year !== undefined ? String(debugInfo.firstResult.year) : 'N/A'}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>doctype</TableCell>
                <TableCell>
                  {debugInfo.firstResult?.doctype !== undefined ? (
                    <Chip label="Yes" size="small" color="success" />
                  ) : (
                    <Chip label="No" size="small" color="error" />
                  )}
                </TableCell>
                <TableCell>{debugInfo.firstResult?.doctype !== undefined ? String(debugInfo.firstResult.doctype) : 'N/A'}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>property</TableCell>
                <TableCell>
                  {debugInfo.firstResult?.property !== undefined ? (
                    <Chip label="Yes" size="small" color="success" />
                  ) : (
                    <Chip label="No" size="small" color="error" />
                  )}
                </TableCell>
                <TableCell>{debugInfo.firstResult?.property !== undefined ? 
                  (Array.isArray(debugInfo.firstResult.property) ? 
                    debugInfo.firstResult.property.join(', ') : 
                    String(debugInfo.firstResult.property)) : 
                  'N/A'}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TableContainer>

        <Typography variant="subtitle2" gutterBottom>Citation Fields</Typography>
        <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Field Name</TableCell>
                <TableCell>Present</TableCell>
                <TableCell>Value</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {Object.entries(debugInfo.citationFields || {}).map(([field, value]) => (
                <TableRow key={field}>
                  <TableCell>{field}</TableCell>
                  <TableCell>
                    {value !== undefined && value !== null ? (
                      <Chip label="Yes" size="small" color="success" />
                    ) : (
                      <Chip label="No" size="small" color="error" />
                    )}
                  </TableCell>
                  <TableCell>{value !== undefined && value !== null ? String(value) : 'N/A'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        
        <Typography variant="subtitle2" gutterBottom>Boost Fields</Typography>
        <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Field Name</TableCell>
                <TableCell>Present</TableCell>
                <TableCell>Value</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {Object.entries(debugInfo.boostFields || {}).map(([field, value]) => (
                <TableRow key={field}>
                  <TableCell>{field}</TableCell>
                  <TableCell>
                    {value !== undefined && value !== null ? (
                      <Chip label="Yes" size="small" color="success" />
                    ) : (
                      <Chip label="No" size="small" color="error" />
                    )}
                  </TableCell>
                  <TableCell>
                    {field === 'boostFactors' && typeof value === 'object' ? (
                      <Typography variant="caption" component="pre" sx={{ maxHeight: 100, overflow: 'auto' }}>
                        {JSON.stringify(value, null, 2)}
                      </Typography>
                    ) : (
                      value !== undefined && value !== null ? String(value) : 'N/A'
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        
        <Typography variant="subtitle2" gutterBottom>First Result Raw Data</Typography>
        <Box 
          component="pre" 
          sx={{ 
            maxHeight: 200, 
            overflow: 'auto', 
            fontSize: '0.75rem', 
            bgcolor: 'grey.100', 
            p: 1, 
            borderRadius: 1 
          }}
        >
          {JSON.stringify(debugInfo.firstResult, null, 2)}
        </Box>
      </Box>
    );
  };
  
  if (!originalResults || originalResults.length === 0) {
    return (
      <Alert severity="warning">
        No results available for boost experiment. Please perform a search first.
      </Alert>
    );
  }
  
  // Function to render boost controls
  const renderBoostControls = () => (
    <Box sx={{ mb: 3 }}>
      <Typography variant="h6" gutterBottom>
        Boost Controls
      </Typography>
      
      {/* Field Boosts */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          Field Boosts
        </Typography>
        <Grid container spacing={2}>
          {Object.entries(boostConfig.fieldBoosts).map(([field, value]) => (
            <Grid item xs={12} sm={6} md={3} key={field}>
              <TextField
                fullWidth
                label={`${field.charAt(0).toUpperCase() + field.slice(1)} Boost`}
                type="number"
                value={value}
                onChange={(e) => handleBoostChange('fieldBoosts', field, e.target.value)}
                inputProps={{ min: 0, step: 0.1 }}
              />
            </Grid>
          ))}
        </Grid>
      </Box>

      {/* Citation Boost */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          Citation Boost
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Citation Boost Factor"
              type="number"
              value={boostConfig.citationBoost}
              onChange={(e) => handleBoostChange('citationBoost', null, e.target.value)}
              inputProps={{ min: 0, step: 0.1 }}
            />
          </Grid>
        </Grid>
      </Box>

      {/* Recency Boost */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          Recency Boost
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="Recency Boost Factor"
              type="number"
              value={boostConfig.recencyBoost}
              onChange={(e) => handleBoostChange('recencyBoost', null, e.target.value)}
              inputProps={{ min: 0, step: 0.1 }}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="Reference Year"
              type="number"
              value={boostConfig.referenceYear}
              onChange={(e) => handleBoostChange('referenceYear', null, e.target.value)}
              inputProps={{ min: 1900, max: new Date().getFullYear() }}
            />
          </Grid>
        </Grid>
      </Box>

      {/* Document Type Boosts */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          Document Type Boosts
        </Typography>
        <Grid container spacing={2}>
          {Object.entries(boostConfig.doctypeBoosts).map(([type, value]) => (
            <Grid item xs={12} sm={6} md={3} key={type}>
              <TextField
                fullWidth
                label={`${type.charAt(0).toUpperCase() + type.slice(1)} Boost`}
                type="number"
                value={value}
                onChange={(e) => handleBoostChange('doctypeBoosts', type, e.target.value)}
                inputProps={{ min: 0, step: 0.1 }}
              />
            </Grid>
          ))}
        </Grid>
      </Box>

      {/* Transformed Query Display */}
      <TransformedQuery query={query} fieldBoosts={boostConfig.fieldBoosts} />

      {/* Run Experiment Button */}
      <Button
        variant="contained"
        onClick={handleRunBoostExperiment}
        disabled={loading || !query}
        sx={{ mt: 2 }}
      >
        {loading ? <CircularProgress size={24} /> : 'Run Boost Experiment'}
      </Button>
    </Box>
  );
  
  return (
    <Box sx={{ width: '100%', p: 2 }}>
      {!originalResults || originalResults.length === 0 ? (
        <Alert severity="warning">
          No results available for boost experiment. Please perform a search first.
        </Alert>
      ) : (
        <Grid container spacing={2}>
          {/* Boost Controls */}
          <Grid item xs={12} md={4}>
            {renderBoostControls()}
          </Grid>

          {/* Results Panel */}
          <Grid item xs={12} md={8}>
            <Paper sx={{ p: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" sx={{ flexGrow: 1 }}>
                  Ranking Results
                </Typography>
                {loading && <CircularProgress size={24} sx={{ ml: 2 }} />}
                <Button
                  startIcon={<BugReportIcon />}
                  variant="outlined"
                  size="small"
                  color="warning"
                  onClick={() => setDebugMode(!debugMode)}
                  sx={{ ml: 2 }}
                >
                  {debugMode ? 'Hide Debug' : 'Debug Mode'}
                </Button>
              </Box>

              {error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {error}
                </Alert>
              )}

              {searchLoading && (
                <Alert severity="info" sx={{ mb: 2 }}>
                  Fetching new results with updated field weights...
                </Alert>
              )}

              <Collapse in={debugMode}>
                {renderDebugPanel()}
              </Collapse>

              {boostedResults && boostedResults.results && Object.keys(boostedResults.results).length > 0 ? (
                <>
                  <Box sx={{ display: 'flex', mb: 2 }}>
                    {/* Title Headers */}
                    <Box sx={{ width: '33%', pr: 1 }}>
                      <Paper sx={{ p: 1, bgcolor: 'grey.100', borderRadius: 1 }}>
                        <Typography variant="subtitle1" align="center" fontWeight="bold">
                          Original Results
                        </Typography>
                        <Typography variant="caption" align="center" display="block" color="text.secondary">
                          Default ranking without boosts
                        </Typography>
                      </Paper>
                    </Box>
                    <Box sx={{ width: '33%', px: 1 }}>
                      <Paper sx={{ p: 1, bgcolor: 'primary.light', color: 'primary.contrastText', borderRadius: 1 }}>
                        <Typography variant="subtitle1" align="center" fontWeight="bold">
                          Boosted Results
                        </Typography>
                        <Typography variant="caption" align="center" display="block" sx={{ color: 'rgba(255,255,255,0.8)' }}>
                          Re-ranked based on current boost settings
                        </Typography>
                      </Paper>
                    </Box>
                    <Box sx={{ width: '33%', pl: 1 }}>
                      <Paper sx={{ p: 1, bgcolor: 'error.light', color: 'error.contrastText', borderRadius: 1 }}>
                        <Typography variant="subtitle1" align="center" fontWeight="bold">
                          Google Scholar Results
                        </Typography>
                        <Typography variant="caption" align="center" display="block" sx={{ color: 'rgba(255,255,255,0.8)' }}>
                          For comparison
                        </Typography>
                      </Paper>
                    </Box>
                  </Box>
                  
                  <Box sx={{ display: 'flex', position: 'relative' }}>
                    {/* Original Results */}
                    <Box sx={{ 
                      width: '33%', 
                      pr: 1, 
                      height: '65vh', 
                      overflow: 'hidden',  // Change from 'auto' to 'hidden'
                      display: 'flex',
                      flexDirection: 'column'
                    }} id="original-results-container">
                      <List sx={{ 
                        bgcolor: 'background.paper', 
                        border: '1px solid', 
                        borderColor: 'divider', 
                        borderRadius: 1,
                        overflow: 'auto',  // Allow only vertical scrolling inside the list
                        overflowX: 'hidden',  // Hide horizontal scrolling
                        flexGrow: 1
                      }}>
                        {originalResults.map((result, index) => {
                          return (
                            <Tooltip
                              key={result.bibcode || index}
                              title={
                                <Box>
                                  <Typography variant="subtitle2">{result.title}</Typography>
                                  <Typography variant="body2">
                                    <strong>Authors:</strong> {formatAuthors(result.author)}
                                  </Typography>
                                  {result.abstract && (
                                    <Typography variant="body2">
                                      <strong>Abstract:</strong> {truncateText(result.abstract, 200)}
                                    </Typography>
                                  )}
                                </Box>
                              }
                              placement="left"
                            >
                              <ListItem 
                                id={`original-item-${index}`}
                                key={result.bibcode || result.title} 
                                divider
                                sx={{ 
                                  px: 2, 
                                  py: 1,
                                  position: 'relative',
                                  transition: 'background-color 0.3s ease',
                                  whiteSpace: 'normal'  // Allow text to wrap
                                }}
                              >
                                <ListItemText
                                  primary={
                                    <Box sx={{ display: 'flex', alignItems: 'flex-start' }}>
                                      <Typography 
                                        variant="body2" 
                                        component="span"
                                        sx={{ 
                                          minWidth: '24px',
                                          fontWeight: 'bold',
                                          mr: 1
                                        }}
                                      >
                                        {index + 1}
                                      </Typography>
                                      <Box sx={{ width: '100%', wordBreak: 'break-word' }}>
                                        <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                                          {truncateText(result.title, 60)}
                                        </Typography>
                                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
                                          {result.year && (
                                            <Chip 
                                              label={`${result.year}`} 
                                              size="small" 
                                              variant="outlined"
                                              sx={{ height: 20, '& .MuiChip-label': { px: 1, fontSize: '0.7rem' } }}
                                            />
                                          )}
                                          {result.citation_count !== undefined && (
                                            <Chip 
                                              label={`Citations: ${result.citation_count}`} 
                                              size="small"
                                              variant="outlined"
                                              sx={{ height: 20, '& .MuiChip-label': { px: 1, fontSize: '0.7rem' } }}
                                            />
                                          )}
                                        </Box>
                                      </Box>
                                    </Box>
                                  }
                                />
                                {boostedResults && boostedResults.results && Array.isArray(boostedResults.results) && (
                                  <Box 
                                    className="connector-point"
                                    data-target={`boosted-item-${boostedResults.results.findIndex(
                                      r => r.bibcode === result.bibcode || r.title === result.title
                                    )}`}
                                    sx={{ 
                                      position: 'absolute', 
                                      right: 0, 
                                      height: '100%', 
                                      width: 4
                                    }} 
                                  />
                                )}
                              </ListItem>
                            </Tooltip>
                          );
                        })}
                      </List>
                    </Box>
                    
                    {/* Boosted Results */}
                    <Box sx={{ 
                      width: '33%', 
                      px: 1, 
                      height: '65vh', 
                      overflow: 'hidden',
                      display: 'flex',
                      flexDirection: 'column'
                    }} id="boosted-results-container">
                      <List sx={{ 
                        bgcolor: 'background.paper', 
                        border: '1px solid', 
                        borderColor: 'primary.light', 
                        borderRadius: 1,
                        overflow: 'auto',
                        overflowX: 'hidden',
                        flexGrow: 1
                      }}>
                        {boostedResults && boostedResults.results && Object.keys(boostedResults.results).length > 0 ? (
                          Object.values(boostedResults.results)[0].map((result, index) => {
                            // Find the original result
                            const originalResult = originalResults.find(
                              r => r.bibcode === result.bibcode || r.title === result.title
                            );
                            const originalIndex = originalResult ? originalResults.indexOf(originalResult) : -1;
                            const rankChange = originalIndex !== -1 ? originalIndex - index : 0;
                            
                            // Determine border style based on magnitude of change
                            let borderStyle = {};
                            if (Math.abs(rankChange) >= 5) {
                              borderStyle = {
                                borderLeft: rankChange !== 0 ? '6px solid' : 'none',
                                borderLeftColor: rankChange > 0 ? 'success.main' : rankChange < 0 ? 'error.main' : 'transparent',
                                bgcolor: rankChange !== 0 ? (rankChange > 0 ? 'success.50' : 'error.50') : 'transparent'
                              };
                            } else if (rankChange !== 0) {
                              borderStyle = {
                                borderLeft: '4px solid',
                                borderLeftColor: rankChange > 0 ? 'success.main' : 'error.main',
                              };
                            }
                            
                            return (
                              <Tooltip
                                key={result.bibcode || index}
                                title={
                                  <Box>
                                    <Typography variant="subtitle2">{result.title}</Typography>
                                    <Typography variant="body2">
                                      <strong>Authors:</strong> {formatAuthors(result.author)}
                                    </Typography>
                                    {result.abstract && (
                                      <Typography variant="body2">
                                        <strong>Abstract:</strong> {truncateText(result.abstract, 200)}
                                      </Typography>
                                    )}
                                    <Divider sx={{ my: 1 }} />
                                    <Typography variant="body2">
                                      <strong>Original Rank:</strong> {originalIndex !== -1 ? originalIndex + 1 : 'N/A'}
                                    </Typography>
                                    <Typography variant="body2">
                                      <strong>Rank Change:</strong> {rankChange > 0 ? '+' : ''}{rankChange}
                                    </Typography>
                                    <Typography variant="body2">
                                      <strong>Boost Score:</strong> {result.boosted_score !== undefined && result.boosted_score !== null ? result.boosted_score.toFixed(2) : 'N/A'}
                                    </Typography>
                                    <Typography variant="body2">
                                      <strong>Applied Boosts:</strong>
                                    </Typography>
                                    <Box component="ul" sx={{ mt: 0.5, pl: 2 }}>
                                      {result.boost_factors && Object.entries(result.boost_factors).map(([key, value]) => (
                                        <Typography component="li" variant="caption" key={key}>
                                          {key}: {value !== undefined && value !== null && typeof value === 'number' ? value.toFixed(2) : value}
                                        </Typography>
                                      ))}
                                    </Box>
                                  </Box>
                                }
                                placement="right"
                              >
                                <ListItem 
                                  id={`boosted-item-${index}`}
                                  key={result.bibcode || result.title} 
                                  divider
                                  sx={{ 
                                    px: 2, 
                                    py: 1,
                                    position: 'relative',
                                    ...borderStyle,
                                    transition: 'background-color 0.3s ease',
                                    whiteSpace: 'normal'
                                  }}
                                >
                                  <ListItemText
                                    primary={
                                      <Box sx={{ display: 'flex', alignItems: 'flex-start' }}>
                                        <Typography 
                                          variant="body2" 
                                          component="span"
                                          sx={{ 
                                            minWidth: '24px',
                                            fontWeight: 'bold',
                                            mr: 1
                                          }}
                                        >
                                          {index + 1}
                                        </Typography>
                                        <Box sx={{ width: '100%', wordBreak: 'break-word' }}>
                                          <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                                            {truncateText(result.title, 60)}
                                          </Typography>
                                          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
                                            {result.year && (
                                              <Chip 
                                                label={`${result.year}`} 
                                                size="small" 
                                                variant="outlined"
                                                sx={{ height: 20, '& .MuiChip-label': { px: 1, fontSize: '0.7rem' } }}
                                              />
                                            )}
                                            {result.citation_count !== undefined && (
                                              <Chip 
                                                label={`Citations: ${result.citation_count}`} 
                                                size="small"
                                                variant="outlined"
                                                sx={{ height: 20, '& .MuiChip-label': { px: 1, fontSize: '0.7rem' } }}
                                              />
                                            )}
                                            {result.boosted_score !== undefined && result.boosted_score !== null && (
                                              <Chip 
                                                label={`Boost: ${result.boosted_score.toFixed(1)}`} 
                                                size="small"
                                                color="primary"
                                                sx={{ 
                                                  height: 20, 
                                                  '& .MuiChip-label': { px: 1, fontSize: '0.7rem' },
                                                  fontWeight: 'bold', 
                                                  bgcolor: `rgba(25, 118, 210, ${Math.min(result.boosted_score / 20, 1)})`
                                                }}
                                              />
                                            )}
                                          </Box>
                                        </Box>
                                      </Box>
                                    }
                                  />
                                  {originalIndex !== -1 && (
                                    <Box 
                                      className="connector-point"
                                      data-target={`original-item-${originalIndex}`}
                                      data-change={rankChange}
                                      sx={{ 
                                        position: 'absolute', 
                                        left: 0, 
                                        height: '100%', 
                                        width: 4
                                      }} 
                                    />
                                  )}
                                </ListItem>
                              </Tooltip>
                            );
                          })
                        ) : (
                          <ListItem>
                            <ListItemText
                              primary="No boosted results available"
                              secondary="Please run a boost experiment to see the results"
                            />
                          </ListItem>
                        )}
                      </List>
                    </Box>

                    {/* Google Scholar Results */}
                    <Box sx={{ 
                      width: '33%', 
                      pl: 1, 
                      height: '65vh', 
                      overflow: 'hidden',  // Change from 'auto' to 'hidden'
                      display: 'flex',
                      flexDirection: 'column'
                    }} id="google-scholar-container">
                      <List sx={{ 
                        bgcolor: 'background.paper', 
                        border: '1px solid', 
                        borderColor: 'error.light', 
                        borderRadius: 1,
                        overflow: 'auto',  // Allow vertical scrolling inside the list
                        overflowX: 'hidden',  // Hide horizontal scrolling
                        flexGrow: 1
                      }}>
                        {results && results.results && results.results.scholar ? (
                          results.results.scholar.map((result, index) => (
                            <Tooltip
                              key={`scholar-${index}`}
                              title={
                                <Box>
                                  <Typography variant="subtitle2">{result.title}</Typography>
                                  <Typography variant="body2">
                                    <strong>Authors:</strong> {formatAuthors(result.authors)}
                                  </Typography>
                                  {result.abstract && (
                                    <Typography variant="body2">
                                      <strong>Abstract:</strong> {truncateText(result.abstract, 200)}
                                    </Typography>
                                  )}
                                </Box>
                              }
                              placement="left"
                            >
                              <ListItem 
                                divider
                                sx={{ 
                                  px: 2, 
                                  py: 1,
                                  position: 'relative',
                                  transition: 'background-color 0.3s ease',
                                  whiteSpace: 'normal'  // Allow text to wrap
                                }}
                              >
                                <ListItemText
                                  primary={
                                    <Box sx={{ display: 'flex', alignItems: 'flex-start' }}>
                                      <Typography 
                                        variant="body2" 
                                        component="span"
                                        sx={{ 
                                          minWidth: '24px',
                                          fontWeight: 'bold',
                                          mr: 1
                                        }}
                                      >
                                        {index + 1}
                                      </Typography>
                                      <Box sx={{ width: '100%', wordBreak: 'break-word' }}>
                                        <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                                          {truncateText(result.title, 60)}
                                        </Typography>
                                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
                                          {result.year && (
                                            <Chip 
                                              label={`${result.year}`} 
                                              size="small" 
                                              variant="outlined"
                                              sx={{ height: 20, '& .MuiChip-label': { px: 1, fontSize: '0.7rem' } }}
                                            />
                                          )}
                                          {result.citation_count !== undefined && (
                                            <Chip 
                                              label={`Citations: ${result.citation_count}`} 
                                              size="small"
                                              variant="outlined"
                                              sx={{ height: 20, '& .MuiChip-label': { px: 1, fontSize: '0.7rem' } }}
                                            />
                                          )}
                                        </Box>
                                      </Box>
                                    </Box>
                                  }
                                />
                                {result.url && (
                                  <IconButton 
                                    size="small" 
                                    href={result.url} 
                                    target="_blank"
                                    aria-label="Open in Google Scholar"
                                  >
                                    <LaunchIcon fontSize="small" />
                                  </IconButton>
                                )}
                              </ListItem>
                            </Tooltip>
                          ))
                        ) : (
                          <ListItem>
                            <ListItemText
                              primary="No Google Scholar results available"
                              secondary="Please run a search with Google Scholar enabled to see comparison results"
                            />
                          </ListItem>
                        )}
                      </List>
                    </Box>
                  </Box>
                  
                  {/* Add useEffect to draw connecting lines between matching items */}
                  <Box component="script" dangerouslySetInnerHTML={{ __html: `
                    // Draw connecting lines between matching items when the component mounts
                    setTimeout(function() {
                      // Remove any existing connectors
                      document.querySelectorAll('.result-connector').forEach(el => el.remove());
                      
                      // For each boosted result, find its original position and draw a line
                      document.querySelectorAll('#boosted-results-container .connector-point').forEach(point => {
                        const targetId = point.getAttribute('data-target');
                        const rankChange = parseInt(point.getAttribute('data-change') || '0');
                        
                        if (!targetId) return;
                        
                        const targetEl = document.getElementById(targetId);
                        if (!targetEl) return;
                        
                        // Get positions
                        const boostedRect = point.getBoundingClientRect();
                        const originalRect = targetEl.getBoundingClientRect();
                        
                        // Create connector
                        const connector = document.createElement('div');
                        connector.className = 'result-connector';
                        
                        // Set style
                        connector.style.position = 'absolute';
                        connector.style.zIndex = '10';
                        connector.style.height = '2px';
                        connector.style.opacity = '0.7';
                        connector.style.pointerEvents = 'none';
                        
                        // Set color based on rank change
                        if (rankChange > 0) {
                          connector.style.backgroundColor = '#4caf50'; // success.main
                        } else if (rankChange < 0) {
                          connector.style.backgroundColor = '#f44336'; // error.main
                        } else {
                          connector.style.backgroundColor = '#9e9e9e'; // grey.500
                        }
                        
                        // Get parent container
                        const container = document.querySelector('.MuiGrid-container');
                        
                        // Calculate positions relative to the container
                        const rect = container.getBoundingClientRect();
                        
                        const fromX = boostedRect.left - rect.left;
                        const fromY = boostedRect.top - rect.top + boostedRect.height / 2;
                        const toX = originalRect.right - rect.left;
                        const toY = originalRect.top - rect.top + originalRect.height / 2;
                        
                        const length = Math.sqrt(Math.pow(toX - fromX, 2) + Math.pow(toY - fromY, 2));
                        const angle = Math.atan2(toY - fromY, toX - fromX) * 180 / Math.PI;
                        
                        // Apply styles
                        connector.style.width = length + 'px';
                        connector.style.left = fromX + 'px';
                        connector.style.top = fromY + 'px';
                        connector.style.transform = 'rotate(' + angle + 'deg)';
                        connector.style.transformOrigin = '0 0';
                        
                        // Add to document
                        container.appendChild(connector);
                      });
                    }, 500);
                  `}} />
                </>
              ) : (
                <Alert severity="info">
                  Configure and apply boost factors to see how they affect the ranking.
                </Alert>
              )}
            </Paper>
          </Grid>
        </Grid>
      )}
    </Box>
  );
};

export default BoostExperiment; 
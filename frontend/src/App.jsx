import React, { useState } from 'react';
import PlotlyChart from './PlotlyChart'; // Assuming PlotlyChart.jsx is in the same directory

// --- Styles ---
// We'll keep styles here for simplicity in this single-file component.
const styles = {
  appWrapper: {
    display: 'flex',
    justifyContent: 'center',
    padding: '40px 20px',
    boxSizing: 'border-box',
    backgroundColor: '#f4f7f6',
    minHeight: '100vh',
  },
  app: {
    width: '100%',
    maxWidth: '800px',
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif",
    color: '#333',
    textAlign: 'center',
  },
  header: {
    marginBottom: '40px',
  },
  h1: {
    fontSize: '2.5em',
    color: '#2c3e50',
    margin: 0,
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '15px',
    marginBottom: '30px',
  },
  inputGroup: {
    display: 'flex',
    gap: '10px',
  },
  input: {
    flexGrow: 1,
    padding: '12px 15px',
    fontSize: '1em',
    borderRadius: '8px',
    border: '1px solid #ccc',
    transition: 'border-color 0.3s, box-shadow 0.3s',
  },
  button: {
    padding: '12px 20px',
    fontSize: '1em',
    border: 'none',
    borderRadius: '8px',
    backgroundColor: '#3498db',
    color: 'white',
    cursor: 'pointer',
    transition: 'background-color 0.3s',
  },
  buttonDisabled: {
    backgroundColor: '#bdc3c7',
    cursor: 'not-allowed',
  },
  results: {
    backgroundColor: 'white',
    padding: '20px',
    borderRadius: '8px',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
    marginTop: '20px',
    minHeight: '100px',
    textAlign: 'left',
  },
  error: {
    color: '#e74c3c',
    fontWeight: 'bold',
  },
  h3: {
    borderBottom: '2px solid #eee',
    paddingBottom: '10px',
    marginTop: '20px',
    marginBottom: '15px',
  },
  dataInfo: {
    textAlign: 'left',
    padding: '15px',
    backgroundColor: '#ecf0f1',
    borderRadius: '8px',
    marginBottom: '20px',
    whiteSpace: 'pre-wrap',
    fontFamily: 'monospace',
    fontSize: '0.9em',
    border: '1px solid #ddd',
  },
  modeSelector: {
    display: 'flex',
    justifyContent: 'center',
    gap: '20px',
    marginBottom: '25px',
    textAlign: 'left',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    marginTop: '20px',
  },
  th: {
    padding: '12px',
    textAlign: 'left',
    borderBottom: '1px solid #ddd',
    backgroundColor: '#ecf0f1',
  },
  td: {
    padding: '12px',
    textAlign: 'left',
    borderBottom: '1px solid #ddd',
  },
  // New style for the SQL code block
  sqlBox: {
    backgroundColor: '#2d2d2d',
    color: '#f8f8f2',
    padding: '15px',
    borderRadius: '8px',
    overflowX: 'auto',
    fontFamily: "'Fira Code', 'Courier New', monospace",
    fontSize: '0.95em',
    whiteSpace: 'pre',
  },
};


function App() {
  // State variables to manage the application's data and UI
  const [sessionId, setSessionId] = useState(null);
  const [dataInfo, setDataInfo] = useState(null);
  const [datasetUrl, setDatasetUrl] = useState('');
  
  const [query, setQuery] = useState('');
  const [analysisResult, setAnalysisResult] = useState(null);
  // Add 'sql' to the available modes
  const [mode, setMode] = useState('informational'); 
  
  // A key to force re-rendering of the Plotly chart
  const [chartRevision, setChartRevision] = useState(0);
  
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Handles loading data from a URL.
   * It sends a POST request to the backend's /load endpoint.
   */
  const handleLoadData = async (event) => {
    event.preventDefault();
    if (!datasetUrl) {
      setError('Please provide a dataset URL.');
      return;
    }
    setIsLoading(true);
    setError(null);
    setDataInfo(null);
    setSessionId(null);
    setAnalysisResult(null);

    try {
      // The backend server is expected to be running on this address.
      const res = await fetch('http://127.0.0.1:5000/load', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dataset_url: datasetUrl }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to load data.');
      
      setDataInfo(data.data_info);
      setSessionId(data.session_id);

    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Handles the analysis request.
   * It sends the user's query and the current mode to the backend's /analyze endpoint.
   */
  const handleAnalyze = async (event) => {
    event.preventDefault();
    if (!query) {
      setError('Please enter a question.');
      return;
    }
    setIsLoading(true);
    setError(null);
    setAnalysisResult(null);

    try {
      const res = await fetch('http://127.0.0.1:5000/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // Send the session_id, query, and selected mode to the backend.
        body: JSON.stringify({ session_id: sessionId, query: query, mode: mode }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to analyze data.');
      
      setAnalysisResult(data);
      // Increment the revision counter to force a re-mount of the chart component if needed.
      setChartRevision(prevRevision => prevRevision + 1);

    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Renders the results based on the response from the backend.
   * It can display a Plotly chart, an SQL query, or an informational summary with data.
   */
  const renderResults = () => {
    if (isLoading && !analysisResult) {
      return <div>Analyzing...</div>;
    }
    if (error) {
      return <div style={styles.error}>Error: {error}</div>;
    }
    if (!analysisResult) {
      return <div>Your results will appear here.</div>;
    }

    // Case 1: The result is a visualization.
    if (analysisResult.visualization) {
      return (
        <PlotlyChart 
          key={chartRevision} // Use key to force remount on new data
          chartJSON={analysisResult.visualization} 
        />
      );
    }
    
    // Case 2: The result is an SQL query (identified by the 'explanation' key).
    if (analysisResult.explanation) {
        return (
            <div>
                <h3 style={styles.h3}>Generated SQL Query</h3>
                <pre style={styles.sqlBox}><code>{analysisResult.message}</code></pre>
                <h3 style={styles.h3}>Explanation</h3>
                <p>{analysisResult.explanation}</p>
            </div>
        )
    }

    // Case 3: The result is informational text and/or tabular data.
    return (
      <div>
        <h3 style={styles.h3}>Summary</h3>
        <p>{analysisResult.message}</p>
        
        {analysisResult.data && analysisResult.data.length > 0 && (
          <>
            <h3 style={styles.h3}>Data</h3>
            <div style={{overflowX: 'auto'}}>
              <table style={styles.table}>
                <thead>
                  <tr>
                    {Object.keys(analysisResult.data[0]).map(key => <th style={styles.th} key={key}>{key}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {analysisResult.data.map((row, index) => (
                    <tr key={index}>
                      {Object.values(row).map((val, i) => <td style={styles.td} key={i}>{String(val)}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    );
  };
  
  /**
   * Gets the placeholder text for the query input based on the current mode.
   */
  const getPlaceholderText = () => {
      switch(mode) {
          case 'informational':
            return 'e.g., What are the total sales?';
          case 'visualization':
            return 'e.g., Plot sales by country';
          case 'sql':
            return 'e.g., Show me the top 5 customers by profit';
          default:
            return 'Ask a question about your data...';
      }
  }

  return (
    <div style={styles.appWrapper}>
      <div style={styles.app}>
        <header style={styles.header}>
          <h1 style={styles.h1}>davi - Data Analyst & Visualizer</h1>
        </header>

        <main>
          {/* Section for loading the dataset */}
          <form onSubmit={handleLoadData} style={styles.form}>
            <div style={styles.inputGroup}>
              <input
                style={styles.input}
                type="text"
                value={datasetUrl}
                onChange={(e) => setDatasetUrl(e.target.value)}
                placeholder="Enter dataset URL (e.g., https://.../data.csv)"
                disabled={isLoading}
              />
              <button 
                style={isLoading && !sessionId ? {...styles.button, ...styles.buttonDisabled} : styles.button} 
                type="submit" 
                disabled={isLoading && !dataInfo}
              >
                {isLoading && !dataInfo ? 'Loading...' : 'Load Data'}
              </button>
            </div>
          </form>

          {/* This section appears after data is successfully loaded */}
          {sessionId && dataInfo && (
            <div className="analysis-section">
              <div style={styles.dataInfo}>
                <strong>Dataset Loaded Successfully!</strong>
                <pre>{dataInfo}</pre>
              </div>
              
              {/* Mode selector with the new SQL option */}
              <div style={styles.modeSelector}>
                <label>
                  <input 
                    type="radio" 
                    value="informational" 
                    checked={mode === 'informational'} 
                    onChange={(e) => setMode(e.target.value)} 
                  />
                  Informational
                </label>
                <label>
                  <input 
                    type="radio" 
                    value="visualization" 
                    checked={mode === 'visualization'} 
                    onChange={(e) => setMode(e.target.value)} 
                  />
                  Visualization
                </label>
                <label>
                  <input 
                    type="radio" 
                    value="sql" 
                    checked={mode === 'sql'} 
                    onChange={(e) => setMode(e.target.value)} 
                  />
                  Natural Language to SQL
                </label>
              </div>

              {/* Form for submitting the analysis query */}
              <form onSubmit={handleAnalyze} style={styles.form}>
                <div style={styles.inputGroup}>
                  <input
                    style={styles.input}
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder={getPlaceholderText()}
                    disabled={isLoading}
                  />
                  <button 
                    style={isLoading ? {...styles.button, ...styles.buttonDisabled} : styles.button} 
                    type="submit" 
                    disabled={isLoading}
                  >
                    {isLoading ? 'Analyzing...' : 'Ask'}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* The results container */}
          <div style={styles.results}>
            {renderResults()}
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;

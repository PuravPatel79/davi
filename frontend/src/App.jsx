import React, { useState } from 'react';
import PlotlyChart from './PlotlyChart'; // Import the new, robust component

// Styles
const styles = {
  appWrapper: {
    display: 'flex',
    justifyContent: 'center',
    padding: '40px 20px',
    boxSizing: 'border-box',
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
  },
  button: {
    padding: '12px 20px',
    fontSize: '1em',
    border: 'none',
    borderRadius: '8px',
    backgroundColor: '#3498db',
    color: 'white',
    cursor: 'pointer',
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
    marginTop: '0',
    marginBottom: '10px',
  },
  dataInfo: {
    textAlign: 'left',
    padding: '10px',
    backgroundColor: '#ecf0f1',
    borderRadius: '8px',
    marginBottom: '20px',
    whiteSpace: 'pre-wrap',
  },
  modeSelector: {
    display: 'flex',
    justifyContent: 'center',
    gap: '20px',
    marginBottom: '15px',
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
  }
};

function App() {
  const [sessionId, setSessionId] = useState(null);
  const [dataInfo, setDataInfo] = useState(null);
  const [datasetUrl, setDatasetUrl] = useState('');
  
  const [query, setQuery] = useState('');
  const [analysisResult, setAnalysisResult] = useState(null);
  const [mode, setMode] = useState('informational');
  
  const [chartRevision, setChartRevision] = useState(0);
  
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

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
        body: JSON.stringify({ session_id: sessionId, query: query, mode: mode }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to analyze data.');
      
      setAnalysisResult(data);
      // Increment the revision counter to force a re-mount of the chart component
      setChartRevision(prevRevision => prevRevision + 1);

    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={styles.appWrapper}>
      <div style={styles.app}>
        <header style={styles.header}>
          <h1 style={styles.h1}>davi - Data Analyst & Visualizer</h1>
        </header>

        <main>
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

          {sessionId && dataInfo && (
            <div className="analysis-section">
              <div style={styles.dataInfo}>
                <strong>Dataset Loaded Successfully!</strong>
                <pre>{dataInfo}</pre>
              </div>
              
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
              </div>

              <form onSubmit={handleAnalyze} style={styles.form}>
                <div style={styles.inputGroup}>
                  <input
                    style={styles.input}
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder={mode === 'visualization' ? 'e.g., Plot sales by country' : 'e.g., What are the total sales?'}
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

          <div style={styles.results}>
            {error && <div style={styles.error}>Error: {error}</div>}
            
            {analysisResult && (
              analysisResult.visualization ? (
                <PlotlyChart 
                  // --- FIX: Use the revision counter as a key to force a full remount ---
                  key={chartRevision}
                  chartJSON={analysisResult.visualization} 
                />
              ) : (
                <div>
                  <h3 style={styles.h3}>Summary</h3>
                  <p>{analysisResult.message}</p>
                  
                  {analysisResult.data && analysisResult.data.length > 0 && (
                    <>
                      <h3 style={styles.h3}>Data</h3>
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
                    </>
                  )}
                </div>
              )
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
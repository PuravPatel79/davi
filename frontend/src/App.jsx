import React, { useState } from 'react';

// Styles are embedded inside the component to make it self-contained.
const styles = {
  app: {
    maxWidth: '800px',
    margin: '0 auto',
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif",
    backgroundColor: '#f4f7f6',
    color: '#333',
    padding: '20px',
    textAlign: 'center',
    minHeight: '100vh',
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
    whiteSpace: 'pre-wrap', // To respect newlines in the data_info string
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
  // State for the two-step process
  const [sessionId, setSessionId] = useState(null);
  const [dataInfo, setDataInfo] = useState(null);
  const [datasetUrl, setDatasetUrl] = useState('');
  
  // State for the analysis step
  const [query, setQuery] = useState('');
  const [analysisResult, setAnalysisResult] = useState(null);
  
  // General UI state
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // --- Handler for Step 1: Loading Data ---
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

  // --- Handler for Step 2: Analyzing Data ---
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
        body: JSON.stringify({ session_id: sessionId, query: query }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to analyze data.');
      
      setAnalysisResult(data);

    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={styles.app}>
      <header style={styles.header}>
        <h1 style={styles.h1}>davi - Data Analyst & Visualizer</h1>
      </header>

      <main>
        {/* --- Data Loading Form (Always visible) --- */}
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
              disabled={isLoading && !sessionId}
            >
              {isLoading && !dataInfo ? 'Loading...' : 'Load Data'}
            </button>
          </div>
        </form>

        {/* --- Analysis Form (Visible only after data is loaded) --- */}
        {sessionId && dataInfo && (
          <div className="analysis-section">
            <div style={styles.dataInfo}>
              <strong>Dataset Loaded Successfully!</strong>
              <pre>{dataInfo}</pre>
            </div>
            <form onSubmit={handleAnalyze} style={styles.form}>
              <div style={styles.inputGroup}>
                <input
                  style={styles.input}
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Now ask a question about the data"
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

        {/* --- Results Display Area --- */}
        <div style={styles.results}>
          {error && <div style={styles.error}>Error: {error}</div>}
          
          {analysisResult && (
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
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
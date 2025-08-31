import React, { useState, useEffect, useRef } from 'react';
import PlotlyChart from './PlotlyChart';
import { io } from 'socket.io-client';
import Editor from 'react-simple-code-editor';
import { highlight, languages } from 'prismjs/components/prism-core';
import 'prismjs/components/prism-python';
import 'prismjs/themes/prism-tomorrow.css';

//Styles
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
    gap: '10px',
    marginBottom: '25px',
    textAlign: 'left',
    flexWrap: 'wrap',
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
  editorContainer: {
    border: '1px solid #ddd',
    borderRadius: '8px',
    marginBottom: '10px',
    fontFamily: "'Fira Code', 'Courier New', monospace",
  },
  editorOutput: {
    backgroundColor: '#f9f9f9',
    border: '1px solid #eee',
    padding: '15px',
    borderRadius: '8px',
    whiteSpace: 'pre-wrap',
    minHeight: '50px',
    fontFamily: 'monospace',
  },
};

const socket = io(); // Initialize socket connection

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

  // New state for code execution mode
  const [sandboxSessionId, setSandboxSessionId] = useState(null);
  const [code, setCode] = useState('');
  const [executionResult, setExecutionResult] = useState(null);
  const [isExecuting, setIsExecuting] = useState(false);

  // WebSocket Connection Handling
  useEffect(() => {
    if (sandboxSessionId) {
      console.log("Establishing WebSocket connection...");
      
      socket.on('connect', () => {
        console.log('Socket connected!');
        socket.emit('register_session', { sandbox_session_id: sandboxSessionId });
      });

      socket.on('code_result', (data) => {
        console.log('Received code result:', data);
        setExecutionResult(data.output || { type: 'text', data: data.error });
        setIsExecuting(false);
      });

      socket.on('disconnect', () => {
        console.log('Socket disconnected.');
      });
      
      if(!socket.connected) {
        socket.connect();
      } else {
        socket.emit('register_session', { sandbox_session_id: sandboxSessionId });
      }

    } else if (socket.connected) {
        console.log("Sandbox session ended, disconnecting socket.");
        socket.disconnect();
    }
    
    return () => {
      if (socket.connected) {
        console.log("Cleaning up WebSocket connection.");
        socket.disconnect();
      }
    };
  }, [sandboxSessionId]);


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
    setSandboxSessionId(null);

    try {
      const res = await fetch('/api/load', {
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
    setExecutionResult(null);

    try {
      if (mode === 'code_execution') {
        const res = await fetch('/api/execute/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, query: query }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to start execution session.');

        setSandboxSessionId(data.sandbox_session_id);
        setCode(data.initial_code);
        setExecutionResult(data.initial_result.output || { type: 'text', data: data.initial_result.error });

      } else {
        setSandboxSessionId(null);
        const res = await fetch('/api/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId, query: query, mode: mode }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to analyze data.');
        
        setAnalysisResult(data);
        if (data.visualization) {
            setChartRevision(prev => prev + 1);
        }
      }

    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleRerunCode = () => {
    if (code && sandboxSessionId && socket.connected) {
        setIsExecuting(true);
        setExecutionResult(null);
        console.log("Emitting 'execute_code' with code:", code);
        socket.emit('execute_code', {
            sandbox_session_id: sandboxSessionId,
            code: code
        });
    } else {
        setError("Cannot execute code. No active session or connection.");
    }
  };

  const renderExecutionOutput = () => {
    if (isExecuting) return "Waiting for result...";
    if (!executionResult) return null;

    if (executionResult.type === 'visualization') {
        let isValidChart = false;
        if (executionResult.data && typeof executionResult.data === 'string') {
            try {
                const parsed = JSON.parse(executionResult.data);
                if (parsed.data && parsed.layout) {
                    isValidChart = true;
                }
            } catch (e) {
                // Not valid JSON
            }
        }

        if (isValidChart) {
            return <PlotlyChart chartJSON={executionResult.data} />;
        } else {
            return (
                <div style={{ color: 'red', fontWeight: 'bold' }}>
                    Error: Received a 'visualization' type result, but the data was not a valid Plotly chart JSON.
                    <pre style={styles.editorOutput}>{executionResult.data}</pre>
                </div>
            );
        }
    }
    
    if (executionResult.type === 'text') {
        return <pre style={styles.editorOutput}>{executionResult.data}</pre>;
    }

    return <pre style={{...styles.editorOutput, color: 'red'}}>{executionResult.data || executionResult}</pre>;
  }

  const renderResults = () => {
    if (isLoading && !analysisResult && !executionResult) {
      return <div>Analyzing...</div>;
    }
    if (error) {
      return <div style={styles.error}>Error: {error}</div>;
    }
    
    if (mode === 'code_execution' && sandboxSessionId) {
        return (
            <div>
                <h3 style={styles.h3}>Interactive Code Editor</h3>
                <div style={styles.editorContainer}>
                    <Editor
                        value={code}
                        onValueChange={c => setCode(c)}
                        highlight={c => highlight(c, languages.python)}
                        padding={10}
                        style={{
                            fontFamily: '"Fira code", "Fira Mono", monospace',
                            fontSize: 14,
                            backgroundColor: '#fdfdfd',
                            minHeight: '200px',
                        }}
                    />
                </div>
                <button 
                    style={isExecuting ? {...styles.button, ...styles.buttonDisabled} : styles.button} 
                    onClick={handleRerunCode}
                    disabled={isExecuting}
                  >
                    {isExecuting ? 'Executing...' : 'Re-run Code'}
                  </button>

                <h3 style={styles.h3}>Execution Output</h3>
                {renderExecutionOutput()}
            </div>
        )
    }

    if (!analysisResult) {
      return <div>Your results will appear here.</div>;
    }

    if (analysisResult.visualization) {
      return (
        <PlotlyChart 
          key={chartRevision}
          chartJSON={analysisResult.visualization} 
        />
      );
    }
    
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

  const getPlaceholderText = () => {
      switch(mode) {
          case 'informational':
            return 'e.g., What are the total sales?';
          case 'visualization':
            return 'e.g., Plot sales by country';
          case 'sql':
            return 'e.g., Show me the top 5 customers by profit';
          case 'code_execution':
            return 'e.g., Create a new column "Sales per Unit"';
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
                  <input type="radio" value="informational" checked={mode === 'informational'} onChange={(e) => setMode(e.target.value)} />
                  Informational
                </label>
                <label>
                  <input type="radio" value="visualization" checked={mode === 'visualization'} onChange={(e) => setMode(e.target.value)} />
                  Visualization
                </label>
                <label>
                  <input type="radio" value="sql" checked={mode === 'sql'} onChange={(e) => setMode(e.target.value)} />
                  NLP to SQL
                </label>
                <label>
                  <input type="radio" value="code_execution" checked={mode === 'code_execution'} onChange={(e) => setMode(e.target.value)} />
                  Direct Code Execution
                </label>
              </div>

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

          <div style={styles.results}>
            {renderResults()}
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
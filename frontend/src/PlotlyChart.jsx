import React, { useRef, useEffect } from 'react';
import Plot from 'react-plotly.js';

function PlotlyChart({ chartJSON }) {
  const chartContainerRef = useRef(null);

  useEffect(() => {
    const adjustContainerHeight = () => {
      if (chartContainerRef.current) {
        const svgElement = chartContainerRef.current.querySelector('.main-svg');
        if (svgElement) {
          const chartHeight = svgElement.getBoundingClientRect().height;
          if (chartHeight > 0) {
            chartContainerRef.current.style.height = `${chartHeight}px`;
          }
        }
      }
    };
    const timer = setTimeout(adjustContainerHeight, 150);
    return () => clearTimeout(timer);
  }, [chartJSON]);

  if (!chartJSON) {
    return <div>No chart data available.</div>;
  }

  let chartData;
  try {
    chartData = JSON.parse(chartJSON);
  } catch (error) {
    console.error("Failed to parse chart JSON:", error);
    return (
      <div style={{ color: 'red', fontWeight: 'bold' }}>
        Error: Could not render the visualization. The data format from the backend was invalid.
      </div>
    );
  }

  // --- FIX IS HERE: Validate the structure of the parsed JSON ---
  if (!chartData.data || !chartData.layout) {
    console.error("Invalid chart data structure:", chartData);
    return (
        <div style={{ color: 'red', fontWeight: 'bold' }}>
            Error: The backend returned a chart object with a missing 'data' or 'layout' property.
        </div>
    );
  }

  return (
    <div ref={chartContainerRef} style={{ width: '100%', height: '450px' }}>
      <Plot
        data={chartData.data}
        layout={{ ...chartData.layout, autosize: true }}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler={true}
        config={{ responsive: true }}
      />
    </div>
  );
}

export default PlotlyChart;
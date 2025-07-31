import React, { useRef, useEffect } from 'react';
import Plot from 'react-plotly.js';

function PlotlyChart({ chartJSON }) {
  const chartContainerRef = useRef(null);

  useEffect(() => {
    // This effect runs after the chart is rendered or updated.
    // It's designed to measure the true height of the SVG chart.
    const adjustContainerHeight = () => {
      if (chartContainerRef.current) {
        const svgElement = chartContainerRef.current.querySelector('.main-svg');
        if (svgElement) {
          const chartHeight = svgElement.getBoundingClientRect().height;
          // Set the container's height to perfectly match the SVG's height.
          if (chartHeight > 0) {
            chartContainerRef.current.style.height = `${chartHeight}px`;
          }
        }
      }
    };

    // Plotly can take a moment to draw. We use a short timeout
    // to ensure we measure the height *after* it has finished rendering.
    const timer = setTimeout(adjustContainerHeight, 150);

    // Cleanup function to prevent memory leaks
    return () => clearTimeout(timer);
  }, [chartJSON]); // This effect re-runs every time a new chart is requested

  if (!chartJSON) {
    return <div>No chart data available.</div>;
  }

  const chartData = JSON.parse(chartJSON);

  return (
    // We attach a 'ref' to this div so our code can find and measure it.
    <div ref={chartContainerRef} style={{ width: '100%', height: '450px' /* An initial height */ }}>
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
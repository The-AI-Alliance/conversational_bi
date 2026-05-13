// Test Sales Data
const salesData = [
    { category: 'Electronics', sales: 45000 },
    { category: 'Clothing', sales: 32000 },
    { category: 'Groceries', sales: 58000 },
    { category: 'Home & Garden', sales: 27000 },
    { category: 'Sports', sales: 19000 },
    { category: 'Books', sales: 12000 },
    { category: 'Toys', sales: 23000 }
];

// Chart dimensions
const margin = { top: 40, right: 30, bottom: 60, left: 80 };
const width = 800 - margin.left - margin.right;
const height = 400 - margin.top - margin.bottom;

// Create SVG container
const svg = d3.select('#sales-chart')
    .append('svg')
    .attr('viewBox', `0 0 ${width + margin.left + margin.right} ${height + margin.top + margin.bottom}`)
    .attr('preserveAspectRatio', 'xMidYMid meet')
    .style('max-width', '800px')
    .style('width', '100%')
    .append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`);

// Create scales
const xScale = d3.scaleBand()
    .domain(salesData.map(d => d.category))
    .range([0, width])
    .padding(0.3);

const yScale = d3.scaleLinear()
    .domain([0, d3.max(salesData, d => d.sales) * 1.1])
    .range([height, 0]);

// Create and add X axis
svg.append('g')
    .attr('class', 'axis x-axis')
    .attr('transform', `translate(0,${height})`)
    .call(d3.axisBottom(xScale))
    .selectAll('text')
    .attr('transform', 'rotate(-25)')
    .style('text-anchor', 'end')
    .attr('dx', '-0.5em')
    .attr('dy', '0.5em');

// Create and add Y axis
svg.append('g')
    .attr('class', 'axis y-axis')
    .call(d3.axisLeft(yScale).tickFormat(d => `$${d3.format(',.0f')(d)}`));

// Y axis label
svg.append('text')
    .attr('class', 'axis-label')
    .attr('transform', 'rotate(-90)')
    .attr('y', -60)
    .attr('x', -height / 2)
    .attr('text-anchor', 'middle')
    .text('Sales ($)');

// Create bars with animation
svg.selectAll('.bar')
    .data(salesData)
    .enter()
    .append('rect')
    .attr('class', 'bar')
    .attr('x', d => xScale(d.category))
    .attr('width', xScale.bandwidth())
    .attr('y', height)
    .attr('height', 0)
    .transition()
    .duration(800)
    .delay((d, i) => i * 100)
    .attr('y', d => yScale(d.sales))
    .attr('height', d => height - yScale(d.sales));

// Add value labels on top of bars
svg.selectAll('.bar-label')
    .data(salesData)
    .enter()
    .append('text')
    .attr('class', 'bar-label')
    .attr('x', d => xScale(d.category) + xScale.bandwidth() / 2)
    .attr('y', d => yScale(d.sales) - 8)
    .attr('text-anchor', 'middle')
    .attr('opacity', 0)
    .text(d => `$${d3.format(',.0f')(d.sales)}`)
    .transition()
    .duration(800)
    .delay((d, i) => i * 100 + 400)
    .attr('opacity', 1);

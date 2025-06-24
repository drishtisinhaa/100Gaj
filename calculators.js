async function submitForm(type) {
    const inputs = document.querySelectorAll('#formContainer input');
    const body = {};
    inputs.forEach(input => body[input.id] = input.value);

    const res = await fetch(`/calculate/${type}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body)
    });
    const result = await res.json();

    let html = '';
    let chartData = null;

    if (type === 'emi') {
        html = `
            <h4>EMI Results:</h4>
            <p><strong>Loan Principal:</strong> ₹${result.principal}</p>
            <p><strong>Monthly EMI:</strong> ₹${result.emi}</p>
            <p><strong>Total Interest:</strong> ₹${result.total_interest}</p>
            <p><strong>Total Payment:</strong> ₹${result.total_payment}</p>
        `;
        chartData = null;
    } else if (type === 'affordability') {
        html = `
            <h4>Affordability Results:</h4>
            <p><strong>Maximum EMI You Can Pay:</strong> ₹${result.max_emi}</p>
            <p><strong>Estimated Affordable Loan Amount:</strong> ₹${result.affordable_loan}</p>
            <p><strong>Estimated Affordable Property Value (with Down Payment):</strong> ₹${result.affordable_property}</p>
        `;
        chartData = {
            labels: ['Expenses', 'Existing EMIs', 'Remaining Income'],
            data: [
                result.expenses,
                result.existing_emis,
                result.remaining_income > 0 ? result.remaining_income : 0
            ],
            colors: ['#f39c12', '#2980b9', '#27ae60'],
            total: result.income
        };
    } else if (type === 'dti') {
        html = `
            <h4>Debt-to-Income Ratio:</h4>
            <p><strong>DTI Ratio:</strong> ${result.dti_ratio}%</p>
            <p><strong>Risk Level:</strong> ${result.risk_level}</p>
        `;
        chartData = {
            labels: ['Debt', 'Remaining Income'],
            data: [
                result.debt,
                result.remaining_income > 0 ? result.remaining_income : 0
            ],
            colors: ['#2980b9', '#27ae60'],
            total: result.income
        };
    } else if (type === 'gratuity') {
        html = `
            <h4>Gratuity Calculation:</h4>
            <p><strong>Gratuity Amount:</strong> ₹${result.gratuity}</p>
        `;
        chartData = null;
    } else if (type === 'retirement') {
        html = `
            <h4>Retirement Planning Results:</h4>
            <p><strong>Estimated Corpus at Retirement:</strong> ₹${result.corpus}</p>
            <p><strong>Required Corpus:</strong> ₹${result.required_corpus}</p>
            <p><strong>Status:</strong> ${result.status}</p>
        `;
        chartData = null;
    } else {
        html = `<p>Invalid calculator type or error.</p>`;
    }

    document.getElementById('resultContainer').innerHTML = html;

    // PIE CHART
    const pie = document.getElementById('pieChart');
    if (chartData && chartData.total > 0) {
        const sum = chartData.data.reduce((a, b) => a + b, 0);
        let data = [...chartData.data];
        let labels = [...chartData.labels];
        let colors = [...chartData.colors];
        if (sum < chartData.total) {
            data.push(chartData.total - sum);
            labels.push('Other/Unallocated');
            colors.push('#bdc3c7');
        }
        pie.style.display = 'block';
        if (window.pieChartObj) window.pieChartObj.destroy();
        window.pieChartObj = new Chart(pie, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: colors,
                    borderColor: '#222',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom',
                        labels: {
                            color: '#ccc',
                            font: { weight: 'bold' }
                        }
                    }
                }
            }
        });
    } else {
        pie.style.display = 'none';
        if (window.pieChartObj) window.pieChartObj.destroy();
    }

    // BAR CHART (for affordability)
    const bar = document.getElementById('barChart');
    if (type === 'affordability') {
        bar.style.display = 'block';
        if (window.barChartObj) window.barChartObj.destroy();
        window.barChartObj = new Chart(bar, {
            type: 'bar',
            data: {
                labels: ['Income', 'Expenses', 'Existing EMIs', 'Remaining Income'],
                datasets: [{
                    label: 'Amount (₹)',
                    data: [
                        result.income,
                        result.expenses,
                        result.existing_emis,
                        result.remaining_income > 0 ? result.remaining_income : 0
                    ],
                    backgroundColor: [
                        '#2980b9',
                        '#f39c12',
                        '#c0392b',
                        '#27ae60'
                    ],
                    borderColor: '#222',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        ticks: { color: '#ccc', font: { weight: 'bold' } }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: { color: '#ccc', font: { weight: 'bold' } }
                    }
                }
            }
        });
    } else {
        bar.style.display = 'none';
        if (window.barChartObj) window.barChartObj.destroy();
    }

    // EMI Amortization Chart (keep as is)
    if (type === 'emi' && result.emi && result.principal && result.total_interest) {
        const tenure = parseInt(body.tenure);
        const rate = parseFloat(body.rate) / (12 * 100);
        let balance = result.principal;
        let principalData = [];
        let interestData = [];
        let labels = [];
        for (let i = 1; i <= tenure; i++) {
            let interest = balance * rate;
            let principalPaid = result.emi - interest;
            balance -= principalPaid;
            principalData.push(principalPaid > 0 ? principalPaid : 0);
            interestData.push(interest > 0 ? interest : 0);
            labels.push(i);
        }
        const amortChart = document.getElementById('amortChart');
        amortChart.style.display = 'block';
        if (window.amortChartObj) window.amortChartObj.destroy();
        window.amortChartObj = new Chart(amortChart, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Principal Paid',
                        data: principalData,
                        borderColor: '#27ae60',
                        backgroundColor: 'rgba(39,174,96,0.1)',
                        fill: true,
                        tension: 0.3
                    },
                    {
                        label: 'Interest Paid',
                        data: interestData,
                        borderColor: '#f39c12',
                        backgroundColor: 'rgba(243,156,18,0.1)',
                        fill: true,
                        tension: 0.3
                    }
                ]
            },
            options: {
                responsive: false,
                plugins: {
                    legend: { display: true, position: 'bottom' }
                },
                scales: {
                    x: { title: { display: true, text: 'Month' } },
                    y: { title: { display: true, text: 'Amount (₹)' } }
                }
            }
        });
    } else {
        const amortChart = document.getElementById('amortChart');
        amortChart.style.display = 'none';
        if (window.amortChartObj) window.amortChartObj.destroy();
    }
}
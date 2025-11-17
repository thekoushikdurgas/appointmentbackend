const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2NjQxOThmNy01OWM4LTQwMzktYTEzYy0zZWFlMGIwMTUxMmUiLCJleHAiOjE3NjMzNzM2OTEsInR5cGUiOiJhY2Nlc3MifQ.0k29Z_8tydAXTlEPhUtyNpQsP9oxkj-_Lc9wCAU8QpM';
// const token = 'YOUR_ACCESS_TOKEN_HERE';

// Test URL - can be modified for different test scenarios
const testUrl = "https://app.apollo.io/#/people?page=1&contactEmailStatusV2[]=verified&contactEmailExcludeCatchAll=true&personTitles[]=Travel%20Manager&personTitles[]=Global%20Travel%20Manager&personTitles[]=Corporate%20Travel%20Manager&personTitles[]=Senior%20Travel%20Manager&personTitles[]=Travel%20Program%20Manager&personTitles[]=Global%20Travel%20Program%20Manager&personTitles[]=Travel%20Operations%20Manager&personTitles[]=Travel%20Services%20Manager&personTitles[]=Travel%20%26%20Expense%20Manager&personTitles[]=T%26E%20Manager&personTitles[]=Travel%20Procurement%20Manager&personTitles[]=Head%20of%20Travel&personTitles[]=Head%20of%20Corporate%20Travel&personTitles[]=Director%20of%20Travel&personTitles[]=Director%20of%20Global%20Travel&personTitles[]=Director%20of%20Travel%20%26%20Expense&personTitles[]=Director%20of%20Travel%20Operations&personTitles[]=Travel%20Procurement%20Director&personTitles[]=Travel%20Category%20Manager&personTitles[]=Senior%20Category%20Manager%20%E2%80%93%20Travel&personTitles[]=Global%20Category%20Manager%20%E2%80%93%20Travel&personTitles[]=Sourcing%20Manager%20%E2%80%93%20Travel&personTitles[]=Strategic%20Sourcing%20Manager%20%28Travel%29&personTitles[]=Finance%20Operations%20Manager&personTitles[]=Expense%20Management%20Manager&personTitles[]=Shared%20Services%20Manager%20%28T%26E%29&personTitles[]=Accounts%20Payable%20Manager&personTitles[]=Controller%20%28T%26E%29&personTitles[]=Expense%20Compliance%20Manager&personTitles[]=Mobility%20Manager&personTitles[]=Global%20Mobility%20Manager&personTitles[]=Employee%20Mobility%20Lead&personTitles[]=Office%20%26%20Travel%20Manager&personTitles[]=VP%20of%20Procurement&personTitles[]=VP%20of%20Operations&personTitles[]=VP%20Finance&personTitles[]=Chief%20Procurement%20Officer&personTitles[]=Chief%20Operating%20Officer&personTitles[]=Travel&personTitles[]=Expense&personTitles[]=Procurement%20Manager&personTitles[]=Senior%20Procurement%20Manager&personTitles[]=Global%20Procurement%20Manager&personTitles[]=Strategic%20Procurement%20Manager&personTitles[]=Procurement%20Operations%20Manager&personTitles[]=Procurement%20Lead&personTitles[]=Procurement%20Specialist&personTitles[]=Procurement%20Analyst&personTitles[]=Purchasing%20Manager&personTitles[]=Senior%20Purchasing%20Manager&personTitles[]=Category%20Manager&personTitles[]=Senior%20Category%20Manager&personTitles[]=Global%20Category%20Manager&personTitles[]=Sourcing%20Manager&personTitles[]=Senior%20Sourcing%20Manager&personTitles[]=Strategic%20Sourcing%20Manager&personTitles[]=Global%20Sourcing%20Manager&personTitles[]=Indirect%20Procurement%20Manager&personTitles[]=Indirect%20Sourcing%20Manager&personTitles[]=Direct%20Procurement%20Manager&personTitles[]=Direct%20Sourcing%20Manager&personTitles[]=Procurement%20%26%20Supply%20Chain%20Manager&personTitles[]=Supplier%20Management%20Manager&personTitles[]=Vendor%20Manager&personTitles[]=Vendor%20Relations%20Manager&personTitles[]=Head%20of%20Procurement&personTitles[]=Head%20of%20Purchasing&personTitles[]=Director%20of%20Procurement&personTitles[]=Director%20of%20Strategic%20Sourcing&personTitles[]=Director%20of%20Purchasing&personTitles[]=T%26E&personSeniorities[]=manager&personSeniorities[]=director&personSeniorities[]=head&personSeniorities[]=vp&personSeniorities[]=partner&personSeniorities[]=c_suite&personSeniorities[]=founder&personSeniorities[]=owner&personSeniorities[]=senior&organizationLocations[]=France&organizationLocations[]=Spain&organizationNumEmployeesRanges[]=501%2C1000&organizationNumEmployeesRanges[]=1001%2C2000&organizationNumEmployeesRanges[]=2001%2C5000&organizationNumEmployeesRanges[]=201%2C500&organizationNumEmployeesRanges[]=101%2C200&organizationNumEmployeesRanges[]=5001%2C10000&organizationNumEmployeesRanges[]=10001&sortByField=%5Bnone%5D&sortAscending=false";

// Use the unified /ws endpoint
const ws = new WebSocket(`ws://127.0.0.1:8000/api/v2/apollo/ws?token=${token}`);

// Track pending requests
const pendingRequests = new Set();

// Request counter for unique request IDs
let requestCounter = 0;

function generateRequestId() {
    return `req-${Date.now()}-${++requestCounter}`;
}

// WebSocket event handlers
ws.on('open', () => {
    console.log('✓ WebSocket connected to Company API\n');
    
    // Example 1: List companies
    setTimeout(() => {
        console.log('1. Listing companies...');
        ws.send(JSON.stringify({
            action: 'list_companies',
            request_id: generateRequestId(),
            data: {
                name: 'Acme',
                employees_min: 100,
                industries: 'Technology,Software',
                limit: 10,
                ordering: '-employees_count'
            }
        }));
    }, 500);
    
    // Example 2: Get a specific company
    setTimeout(() => {
        console.log('2. Getting company by UUID...');
        ws.send(JSON.stringify({
            action: 'get_company',
            request_id: generateRequestId(),
            data: {
                company_uuid: '398cce44-233d-5f7c-aea1-e4a6a79df10c'
            }
        }));
    }, 1500);
    
    // Example 3: Count companies
    setTimeout(() => {
        console.log('3. Counting companies...');
        ws.send(JSON.stringify({
            action: 'count_companies',
            request_id: generateRequestId(),
            data: {
                industries: 'Technology',
                employees_min: 100
            }
        }));
    }, 2500);
    
    // Example 4: Get company UUIDs
    setTimeout(() => {
        console.log('4. Getting company UUIDs...');
        ws.send(JSON.stringify({
            action: 'get_company_uuids',
            request_id: generateRequestId(),
            data: {
                industries: 'Technology',
                employees_min: 100,
                limit: 50
            }
        }));
    }, 3500);
    
    // Example 5: List company names
    setTimeout(() => {
        console.log('5. Listing company names...');
        ws.send(JSON.stringify({
            action: 'list_company_names',
            request_id: generateRequestId(),
            data: {
                search: 'acme',
                limit: 20,
                ordering: 'value'
            }
        }));
    }, 4500);
    
    // Example 6: List industries
    setTimeout(() => {
        console.log('6. Listing industries...');
        ws.send(JSON.stringify({
            action: 'list_industries',
            request_id: generateRequestId(),
            data: {
                separated: true,
                ordering: '-count',
                limit: 20
            }
        }));
    }, 5500);
    
    // Example 7: List keywords
    setTimeout(() => {
        console.log('7. Listing keywords...');
        ws.send(JSON.stringify({
            action: 'list_keywords',
            request_id: generateRequestId(),
            data: {
                separated: true,
                search: 'cloud',
                limit: 20
            }
        }));
    }, 6500);
    
    // Example 8: List technologies
    setTimeout(() => {
        console.log('8. Listing technologies...');
        ws.send(JSON.stringify({
            action: 'list_technologies',
            request_id: generateRequestId(),
            data: {
                separated: true,
                search: 'python',
                ordering: '-count'
            }
        }));
    }, 7500);
    
    // Example 9: List company cities
    setTimeout(() => {
        console.log('9. Listing company cities...');
        ws.send(JSON.stringify({
            action: 'list_company_cities',
            request_id: generateRequestId(),
            data: {
                search: 'san',
                limit: 20,
                ordering: '-count'
            }
        }));
    }, 8500);
    
    // Example 10: List company states
    setTimeout(() => {
        console.log('10. Listing company states...');
        ws.send(JSON.stringify({
            action: 'list_company_states',
            request_id: generateRequestId(),
            data: {
                limit: 20,
                ordering: '-count'
            }
        }));
    }, 9500);
    
    // Example 11: List company countries
    setTimeout(() => {
        console.log('11. Listing company countries...');
        ws.send(JSON.stringify({
            action: 'list_company_countries',
            request_id: generateRequestId(),
            data: {
                limit: 20,
                ordering: '-count'
            }
        }));
    }, 10500);
    
    // Example 12: List company addresses
    setTimeout(() => {
        console.log('12. Listing company addresses...');
        ws.send(JSON.stringify({
            action: 'list_company_addresses',
            request_id: generateRequestId(),
            data: {
                search: 'San Francisco',
                limit: 20
            }
        }));
    }, 11500);
    
    // Example 13: List company contacts
    setTimeout(() => {
        console.log('13. Listing company contacts...');
        ws.send(JSON.stringify({
            action: 'list_company_contacts',
            request_id: generateRequestId(),
            data: {
                company_uuid: '398cce44-233d-5f7c-aea1-e4a6a79df10c',
                title: 'engineer',
                seniority: 'senior',
                limit: 25,
                offset: 0
            }
        }));
    }, 12500);
    
    // Example 14: Count company contacts
    setTimeout(() => {
        console.log('14. Counting company contacts...');
        ws.send(JSON.stringify({
            action: 'count_company_contacts',
            request_id: generateRequestId(),
            data: {
                company_uuid: '398cce44-233d-5f7c-aea1-e4a6a79df10c',
                title: 'engineer'
            }
        }));
    }, 13500);
    
    // Example 15: Get company contact UUIDs
    setTimeout(() => {
        console.log('15. Getting company contact UUIDs...');
        ws.send(JSON.stringify({
            action: 'get_company_contact_uuids',
            request_id: generateRequestId(),
            data: {
                company_uuid: '398cce44-233d-5f7c-aea1-e4a6a79df10c',
                title: 'engineer',
                limit: 100
            }
        }));
    }, 14500);
    
    // Example 16: List company contact first names
    setTimeout(() => {
        console.log('16. Listing company contact first names...');
        ws.send(JSON.stringify({
            action: 'list_company_contact_first_names',
            request_id: generateRequestId(),
            data: {
                company_uuid: '398cce44-233d-5f7c-aea1-e4a6a79df10c',
                search: 'john',
                limit: 25
            }
        }));
    }, 15500);
    
    // Example 17: List company contact last names
    setTimeout(() => {
        console.log('17. Listing company contact last names...');
        ws.send(JSON.stringify({
            action: 'list_company_contact_last_names',
            request_id: generateRequestId(),
            data: {
                company_uuid: '398cce44-233d-5f7c-aea1-e4a6a79df10c',
                limit: 25
            }
        }));
    }, 16500);
    
    // Example 18: List company contact titles
    setTimeout(() => {
        console.log('18. Listing company contact titles...');
        ws.send(JSON.stringify({
            action: 'list_company_contact_titles',
            request_id: generateRequestId(),
            data: {
                company_uuid: '398cce44-233d-5f7c-aea1-e4a6a79df10c',
                search: 'engineer',
                limit: 50
            }
        }));
    }, 17500);
    
    // Example 19: List company contact seniorities
    setTimeout(() => {
        console.log('19. Listing company contact seniorities...');
        ws.send(JSON.stringify({
            action: 'list_company_contact_seniorities',
            request_id: generateRequestId(),
            data: {
                company_uuid: '398cce44-233d-5f7c-aea1-e4a6a79df10c',
                limit: 25
            }
        }));
    }, 18500);
    
    // Example 20: List company contact departments
    setTimeout(() => {
        console.log('20. Listing company contact departments...');
        ws.send(JSON.stringify({
            action: 'list_company_contact_departments',
            request_id: generateRequestId(),
            data: {
                company_uuid: '398cce44-233d-5f7c-aea1-e4a6a79df10c',
                limit: 25
            }
        }));
    }, 19500);
    
    // Example 21: List company contact email statuses
    setTimeout(() => {
        console.log('21. Listing company contact email statuses...');
        ws.send(JSON.stringify({
            action: 'list_company_contact_email_statuses',
            request_id: generateRequestId(),
            data: {
                company_uuid: '398cce44-233d-5f7c-aea1-e4a6a79df10c',
                limit: 25
            }
        }));
    }, 20500);
    
    // // Example 22: Create company (requires admin + write key)
    // setTimeout(() => {
    //     console.log('22. Creating company (requires admin + write key)...');
    //     ws.send(JSON.stringify({
    //         action: 'create_company',
    //         request_id: generateRequestId(),
    //         data: {
    //             write_key: WRITE_KEY,
    //             name: 'New Company Inc',
    //             employees_count: 150,
    //             industries: ['Technology', 'Software'],
    //             keywords: ['startup', 'saas'],
    //             address: '456 Tech Street',
    //             annual_revenue: 10000000,
    //             technologies: ['Python', 'React'],
    //             metadata: {
    //                 city: 'San Francisco',
    //                 state: 'CA',
    //                 country: 'United States',
    //                 website: 'https://newcompany.com'
    //             }
    //         }
    //     }));
    // }, 21500);
    
    // // Example 23: Update company (requires admin + write key)
    // setTimeout(() => {
    //     console.log('23. Updating company (requires admin + write key)...');
    //     ws.send(JSON.stringify({
    //         action: 'update_company',
    //         request_id: generateRequestId(),
    //         data: {
    //             write_key: WRITE_KEY,
    //             company_uuid: '398cce44-233d-5f7c-aea1-e4a6a79df10c',
    //             name: 'Updated Company Name',
    //             employees_count: 300
    //         }
    //     }));
    // }, 22500);
    
    // // Example 24: Delete company (requires admin + write key)
    // setTimeout(() => {
    //     console.log('24. Deleting company (requires admin + write key)...');
    //     ws.send(JSON.stringify({
    //         action: 'delete_company',
    //         request_id: generateRequestId(),
    //         data: {
    //             write_key: WRITE_KEY,
    //             company_uuid: '398cce44-233d-5f7c-aea1-e4a6a79df10c'
    //         }
    //     }));
    // }, 23500);
    
    // Close connection after all examples
    setTimeout(() => {
        console.log('\n✓ All examples completed. Closing connection...');
        ws.close();
    }, 24500);
});

ws.on('message', (data) => {
    try {
        const response = JSON.parse(data.toString());
        
        if (response.status === 'success') {
            console.log(`\n✓ Success [${response.action}] (request_id: ${response.request_id})`);
            
            // Format output based on action type
            if (response.action === 'list_companies' || response.action === 'list_company_contacts') {
                console.log(`  Results: ${response.data.results?.length || 0} items`);
                if (response.data.next) {
                    console.log(`  Has next page: Yes`);
                }
            } else if (response.action === 'count_companies' || response.action === 'count_company_contacts') {
                console.log(`  Count: ${response.data.count}`);
            } else if (response.action === 'get_company_uuids' || response.action === 'get_company_contact_uuids') {
                console.log(`  Count: ${response.data.count}, UUIDs: ${response.data.uuids?.length || 0}`);
            } else if (response.action.includes('list_') && response.data.results) {
                console.log(`  Results: ${response.data.results.length} items`);
                if (response.data.results.length > 0 && response.data.results.length <= 5) {
                    console.log(`  Sample: ${JSON.stringify(response.data.results.slice(0, 3))}`);
                }
            } else if (response.action === 'get_company') {
                console.log(`  Company: ${response.data.name || 'N/A'} (${response.data.uuid})`);
            } else if (response.action === 'create_company' || response.action === 'update_company') {
                console.log(`  Company: ${response.data.name || 'N/A'} (${response.data.uuid})`);
            } else if (response.action === 'delete_company') {
                console.log(`  Company deleted successfully`);
            }
        } else {
            console.error(`\n✗ Error [${response.action}] (request_id: ${response.request_id})`);
            console.error(`  Code: ${response.error?.code || 'unknown'}`);
            console.error(`  Message: ${response.error?.message || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error parsing WebSocket message:', error);
        console.error('Raw data:', data.toString());
    }
});

ws.on('error', (error) => {
    console.error('WebSocket error:', error);
});

ws.on('close', (code, reason) => {
    console.log(`\nWebSocket closed: code=${code}, reason=${reason.toString()}`);
});

// Handle graceful shutdown
process.on('SIGINT', () => {
    console.log('\n\nShutting down...');
    if (ws.readyState === WebSocket.OPEN) {
        ws.close();
    }
    process.exit(0);
});


const fs = require('fs');
const path = require('path');

// Files to fix
const files = [
    'src/components/ManagerDashboard.tsx',
    'src/components/WorkInbox.tsx',
    'src/components/ApprovalQueue.tsx',
    'src/components/AnalyticsDashboard.tsx'
];

files.forEach(filePath => {
    const fullPath = path.join(__dirname, filePath);
    console.log(`\nFixing imports in ${filePath}...`);

    try {
        let content = fs.readFileSync(fullPath, 'utf8');

        // Remove the incorrect Grid2 import line
        content = content.replace(/import Grid2 from '@mui\/material\/Unstable_Grid2';\n/g, '');

        // Replace Grid2 imports with the correct one from @mui/material
        // Check if Grid is in the import statement
        if (content.includes("from '@mui/material';")) {
            // Add Grid2 to the import list
            content = content.replace(
                /(\s+Grid,)/,
                '$1\n    Grid2,'
            );

            // If Grid isn't there but we still need Grid2
            if (!content.includes('Grid,')) {
                content = content.replace(
                    /(Box,)/,
                    '$1\n    Grid2,'
                );
            }
        }

        // Ensure Grid2 is imported
        if (!content.includes('Grid2,')) {
            content = content.replace(
                /from '@mui\/material';/,
                `, Grid2 from '@mui/material';`
            );
        }

        fs.writeFileSync(fullPath, content, 'utf8');
        console.log(`✅ Fixed imports in ${filePath}`);
    } catch (error) {
        console.error(`❌ Error fixing ${filePath}:`, error.message);
    }
});

console.log('\n🎉 All Grid2 imports fixed!');

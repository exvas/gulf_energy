# Gulf Energy - Comprehensive Investor Management System

A sophisticated Frappe application designed for Gulf Energy Trading Company, featuring complete investor lifecycle management, multi-currency support, automated dividend processing, and intelligent project status automation.

## 🚀 Core Features

### 📊 Advanced Investor Management
- **Multi-Currency Investment Tracking**: Support for investments in different currencies with automatic conversion
- **Smart Account Creation**: Generates sequential investor accounts (I3001-I3999) with intelligent reuse logic
- **Account Reuse System**: Prevents duplicate accounts for same investor-project combinations
- **Real-time Exchange Rates**: Fetches current exchange rates from ERPNext Currency Exchange with manual override
- **Project Integration**: Links investments to specific projects for detailed tracking and reporting
- **Automated Journal Entries**: Creates and submits journal entries automatically upon investment submission

### 💰 Dividend Processing & Distribution
- **Investor Closing Voucher**: Comprehensive dividend processing system for bulk operations
- **Automated Dividend Calculations**: Smart calculation of eligible dividend amounts per investor
- **Duplicate Prevention**: Sophisticated system prevents processing same investors multiple times
- **Processing History**: Complete audit trail of all dividend distributions with detailed tracking
- **Journal Entry Automation**: Automatic creation of dividend distribution journal entries
- **Bulk Processing**: Handle multiple investors in single voucher with validation

### 🎯 Project Status Automation
- **Intelligent Project Completion**: Automatically marks projects as "Completed" when all investors processed
- **Manual Override**: "Force Complete Project" button for edge cases and special circumstances
- **Status Validation**: Checks for remaining unprocessed investors before project completion
- **Audit Trail**: Complete project status history with user comments and timestamps
- **Reversion Logic**: Automatically reverts project status on voucher cancellation

### 🔄 Complete Investor Lifecycle
1. **Investment Entry** → Creates investor account with reuse logic
2. **Multi-Project Support** → Same investor can invest in multiple projects
3. **Dividend Processing** → Bulk dividend distribution via Investor Closing Voucher
4. **Automated Accounting** → Journal entries for both investments and dividends
5. **Project Completion** → Automatic status updates when all investors processed
6. **Audit & Compliance** → Complete processing history and comments

### 💰 Currency & Exchange Rate Management
- **Live Exchange Rate Fetching**: Integrates with ERPNext's currency exchange system
- **Manual Rate Override**: Allows users to adjust exchange rates when needed
- **Multi-Currency Display**: Shows amounts in both invested currency and company base currency
- **Real-time Conversion**: Automatic calculation of converted amounts with visual feedback

### 🏦 Automated Accounting
- **Sequential Account Numbering**: I3001, I3002, I3003... format for investor accounts
- **Clean Account Structure**: Eliminates duplicate naming conventions
- **Automated Journal Entries**: 
  - Debits: Amount Received Account (Bank/Cash)
  - Credits: Investor Account (Capital)
- **Project Tagging**: All journal entries tagged with associated projects
- **Proper Dating**: Uses investment date for all accounting entries

## 📋 Installation

### Prerequisites
- Frappe Framework
- ERPNext (for currency exchange functionality)
- Python 3.8+

### Install via Bench

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/your-repo/gulf_energy --branch main
bench install-app gulf_energy
```

### Post-Installation Setup

1. **Create Account Structure** (if not exists):
```python
# Run in Frappe console
exec(open('/path/to/setup_investor_accounts.py').read())
```

2. **Migrate Database**:
```bash
bench migrate
```

## 🎯 Usage

### 📋 Investment Management Workflow

#### Creating an Investment Record

1. **Basic Information**:
   - Investor Name/Company
   - Investment Date
   - Country
   - Invested Company

2. **Financial Details**:
   - Invested Currency (auto-fetches exchange rate)
   - Invested Amount
   - Exchange Rate (editable)
   - Company Currency (auto-filled)
   - Converted Amount (auto-calculated)

3. **Project & Account Selection**:
   - Invested Project (filtered by company)
   - Amount Received Account (Bank/Cash accounts only)

4. **Preview & Submit**:
   - Use "Preview Account Name" to see what will be created
   - Submit to create investor account and journal entry

### 💼 Dividend Processing Workflow

#### Using Investor Closing Voucher

1. **Create New Voucher**:
   - Select Company and Project
   - Set Posting Date and Dividend Return Date
   - Status automatically set to "Draft"

2. **Fetch Project Investors**:
   - Click "Fetch Project Investors" button (appears when Company + Project selected)
   - System automatically loads all investors for the project
   - Excludes investors already processed in previous vouchers
   - Shows duplicate prevention messages

3. **Review and Process**:
   - Review investor list and dividend amounts
   - Modify dividend percentages if needed
   - Submit voucher to process dividends

4. **Automated Operations on Submit**:
   - Creates dividend distribution journal entries
   - Updates project status to "Completed" if all investors processed
   - Adds audit comments to project
   - Prevents duplicate processing

#### Processing History and Audit

1. **View Processing History**:
   - Click "View Processing History" button
   - Shows all previous dividend distributions for the project
   - Displays investor details, amounts, and dates
   - Complete audit trail for compliance

2. **Force Complete Project** (for edge cases):
   - Available in Actions menu for submitted vouchers
   - Manually marks project as completed
   - Includes confirmation dialog and audit trail
   - Use when special circumstances require manual completion

### 🔄 Account Reuse Logic

The system intelligently handles account creation:

- **New Investor + New Project**: Creates new account (e.g., I3001 - Investor Name - Project)
- **Same Investor + Same Project**: Reuses existing account
- **Same Investor + Different Project**: Creates new account with project suffix
- **Sequential Numbering**: I3001, I3002, I3003... continues even with reuse

### Account Numbering System

| Investor | Project | Account Number | Account Name | Display |
|----------|---------|----------------|--------------|---------|
| DesignMelt | PROJ-001 | I3001 | DesignMelt | I3001 - DesignMelt - PROJ-001 |
| ABC Corp | PROJ-001 | I3002 | ABC Corp | I3002 - ABC Corp - PROJ-001 |
| DesignMelt | PROJ-002 | I3003 | DesignMelt | I3003 - DesignMelt - PROJ-002 |
| ABC Corp | PROJ-001 | I3002 | ABC Corp | I3002 - ABC Corp - PROJ-001 (Reused) |

### Automated Journal Entry Structures

#### Investment Journal Entry
```
Dr. Bank Account (Amount Received Account)     XXX.XX
    Cr. I30XX - Investor Name (Investor Account)     XXX.XX

Description: "Investment by [Investor] - [Record ID] (Project: [Project Name])"
Date: Investment Date
Project: Associated Project (if selected)
```

#### Dividend Distribution Journal Entry
```
Dr. I30XX - Investor Name (Investor Account)     XXX.XX
    Cr. Bank Account (Dividend Payment Account)     XXX.XX

Description: "Dividend payment to [Investor] - [Voucher ID] (Project: [Project Name])"
Date: Dividend Return Date
Project: Associated Project
```

## 🔧 Configuration

### Currency Exchange Setup
- Ensure Currency Exchange doctype has current rates
- System automatically fetches rates but allows manual override
- Exchange rates are fetched based on investment date

### Account Structure Requirements
```
3000 - Equity (Group)
  └── 3110 - Investor Capital (Group)
      └── I30XX - Individual Investor Accounts (Ledger)
```

### Project Setup
- Projects must be active and belong to the selected company
- Projects are automatically filtered based on company selection
- Completed and cancelled projects are excluded from selection

## 📊 DocTypes & Field Reference

### 👤 Investor DocType

| Field | Type | Description | Auto-Filled |
|-------|------|-------------|-------------|
| Investor Name/Company | Data | Name of investor | ❌ |
| Invested Currency | Link | Investment currency | ❌ |
| Invested Amount | Currency | Amount in invested currency | ❌ |
| Exchange Rate | Float | Currency conversion rate | ✅ (editable) |
| Company Currency | Data | Base currency | ✅ |
| Invested Amount (Company Currency) | Currency | Converted amount | ✅ |
| Invested Project | Link | Associated project | ❌ |
| Project Name | Data | Project display name | ✅ |
| Invested Company | Link | Receiving company | ❌ |
| Country | Link | Investor's country | ❌ |
| Amount Received Account | Link | Bank/Cash account | ❌ |
| Investor Account | Link | Auto-created/reused account | ✅ |
| Journal Entry | Link | Generated entry | ✅ |

### 💰 Investor Closing Voucher DocType

| Field | Type | Description | Auto-Filled |
|-------|------|-------------|-------------|
| Series | Data | Naming series (ICV-YYYY-) | ✅ |
| Company | Link | Processing company | ❌ |
| Project | Link | Project for dividend processing | ❌ |
| Project Name | Data | Project display name | ✅ |
| Posting Date | Date | Voucher posting date | ❌ |
| Dividend Return Date | Date | Dividend payment date | ❌ |
| Status | Select | Draft/Submitted/Cancelled | ✅ |
| Total Investors | Int | Number of investors | ✅ |
| Total Investment | Currency | Sum of investments | ✅ |
| Total Dividend Amount | Currency | Sum of dividends | ✅ |

### 📋 Investor Closing Detail (Child Table)

| Field | Type | Description | Auto-Filled |
|-------|------|-------------|-------------|
| Investor Name | Link | Reference to investor | ❌ |
| Investor ID | Data | Unique investor identifier | ✅ |
| Investor Account | Link | Investor's account | ✅ |
| Invested Amount | Currency | Original investment | ✅ |
| Dividend % | Float | Dividend percentage | ❌ |
| Eligible Dividend Amount | Currency | Calculated dividend | ✅ |
| Dividend Return Date | Date | Payment date | ✅ |

## 🛠️ Technical Architecture

### Client-Side (JavaScript)
- **Real-time Calculations**: Automatic currency conversions and dividend calculations
- **Smart Filtering**: Context-aware dropdown filters for projects and accounts
- **User Feedback**: Visual indicators, notifications, and processing status updates
- **Validation**: Pre-submission checks, duplicate prevention, and data integrity
- **Dynamic UI**: Button visibility based on document state and field values
- **Processing History**: Interactive display of dividend distribution history

### Server-Side (Python)
- **Account Management**: Sequential numbering with intelligent reuse logic
- **Journal Entry Automation**: Automated creation for investments and dividends
- **Project Integration**: Cross-module linking and status automation
- **Duplicate Prevention**: Sophisticated validation to prevent duplicate processing
- **Error Handling**: Comprehensive validation and error management
- **Audit Trail**: Complete transaction history with user tracking

### Key Methods & Functions

#### Investor DocType
- `find_existing_investor_account()`: Account reuse logic
- `create_investor_account()`: Sequential account generation
- `create_journal_entry()`: Investment journal entry creation
- `get_exchange_rate()`: Currency rate fetching

#### Investor Closing Voucher DocType
- `fetch_project_investors()`: Load unprocessed investors
- `create_dividend_journal_entries()`: Bulk dividend processing
- `update_project_status()`: Intelligent project completion
- `force_complete_project()`: Manual project completion override
- `get_investor_processing_history()`: Audit trail retrieval

### Database Structure
- **Submittable DocTypes**: Support draft/submitted workflow with cancellation
- **Proper Indexing**: Optimized for reporting, searches, and duplicate detection
- **Audit Trail**: Complete transaction history with timestamps and user tracking
- **Data Integrity**: Foreign key relationships and validation constraints

## 📈 Reporting & Analytics

### Available Reports
- **Investor-wise Investment Summary**: Complete investment history per investor
- **Project-wise Investment Tracking**: Total investments and dividends per project
- **Currency-wise Investment Analysis**: Multi-currency investment breakdowns
- **Monthly/Yearly Investment Trends**: Time-based investment patterns
- **Dividend Distribution Reports**: Complete dividend processing history
- **Project Status Reports**: Project completion tracking with investor counts
- **Account Reuse Analytics**: Statistics on account reuse and efficiency

### Processing History Features
- **Complete Audit Trail**: Every dividend distribution tracked with timestamps
- **Investor-level Details**: Individual investor processing history
- **Voucher-level Summary**: Bulk processing summaries with totals
- **Project Completion Timeline**: Track when projects were marked as completed
- **User Activity Logs**: Who processed what and when

### Integration Points
- **ERPNext Accounting**: Full integration with chart of accounts and journal entries
- **Project Management**: Complete integration with ERPNext project module
- **Currency Management**: Uses ERPNext currency system with real-time rates
- **Reporting**: Compatible with ERPNext report builder and custom reports
- **Dashboard Integration**: Custom dashboards for investor and project analytics

## 🔒 Security & Permissions

### Role-Based Access
- **System Manager**: Full access to all features including force complete project
- **Accounts Manager**: Investment and dividend processing capabilities
- **Accounts User**: Read-only access to investment and dividend records
- **Project Manager**: Can view project-related investment data

### Data Validation & Integrity
- **Currency Validation**: Ensures valid currency combinations and exchange rates
- **Account Validation**: Verifies account-company relationships and prevents orphaned accounts
- **Project Validation**: Confirms project-company alignment and active status
- **Amount Validation**: Prevents negative or zero investments and dividends
- **Duplicate Prevention**: Sophisticated checks prevent duplicate investor processing
- **Date Validation**: Ensures logical date sequences and prevents future dating
- **Permission Checks**: Validates user permissions for sensitive operations

## 🧪 Testing & Quality Assurance

### Manual Testing Checklist

#### Investment Module
- [ ] Create investor with same currency (exchange rate = 1)
- [ ] Create investor with different currency (auto exchange rate)
- [ ] Test manual exchange rate override
- [ ] Verify sequential account number generation
- [ ] Test account reuse for same investor-project combinations
- [ ] Test project assignment in journal entries
- [ ] Validate account filtering by company
- [ ] Test preview functionality
- [ ] Verify cancellation workflow

#### Dividend Processing Module
- [ ] Create Investor Closing Voucher and fetch investors
- [ ] Test duplicate prevention when fetching same project investors
- [ ] Verify dividend calculations and totals
- [ ] Test bulk dividend journal entry creation
- [ ] Validate processing history display
- [ ] Test project auto-completion when all investors processed
- [ ] Test force complete project functionality
- [ ] Verify voucher cancellation and project status reversion

#### Integration Testing
- [ ] Multi-project investor account creation
- [ ] Cross-project dividend processing
- [ ] Project status automation with multiple vouchers
- [ ] Currency conversion accuracy across modules
- [ ] Permission-based access control
- [ ] Data integrity after cancellations and resubmissions

### Automated Testing
```bash
# Run all tests
bench run-tests gulf_energy

# Run specific test files
bench run-tests gulf_energy.tests.test_investor
bench run-tests gulf_energy.tests.test_investor_closing_voucher

# Run with coverage
bench run-tests gulf_energy --coverage
```

### Performance Testing
- **Large Dataset Handling**: Test with 1000+ investors and 100+ projects
- **Concurrent Processing**: Multiple users processing dividends simultaneously
- **Account Reuse Efficiency**: Performance impact of account reuse logic
- **Report Generation**: Large-scale report performance and accuracy

## 📚 Additional Documentation

- [Detailed Setup Guide](INVESTOR_MODULE_README.md)
- [API Documentation](docs/api.md)
- [Troubleshooting Guide](docs/troubleshooting.md)

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app gulf_energy
```

## 🤝 Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/gulf_energy
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### Development Workflow
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `bench run-tests gulf_energy`
5. Submit a pull request

### Code Standards
- Follow PEP 8 for Python code
- Use ES6+ standards for JavaScript
- Document all new features
- Include unit tests for new functionality

## 🔄 CI/CD Pipeline

This app can use GitHub Actions for CI. The following workflows are configured:

- **CI**: Installs this app and runs unit tests on every push to `develop` branch
- **Linters**: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request
- **Deploy**: Automated deployment to staging/production environments

## 🆘 Support

### Getting Help
- **Documentation**: Check the detailed guides in the `docs/` folder
- **Issues**: Report bugs and feature requests via GitHub Issues
- **Community**: Join the Frappe community forum for general discussions

### Common Issues & Solutions

#### Investment Module Issues
- **Exchange Rate Not Found**: Ensure Currency Exchange records exist in ERPNext
- **Account Creation Failed**: Verify "3110 - Investor Capital" account exists
- **Permission Errors**: Check user roles and permissions for Account creation
- **Duplicate Account Names**: System now prevents duplicates with intelligent reuse

#### Dividend Processing Issues
- **"Fetch Project Investors" Button Missing**: Ensure both Company and Project are selected
- **Duplicate Processing Error**: System prevents same investor being processed twice
- **Project Not Found Error**: Verify project exists and is active in the system
- **Force Complete Project Not Working**: Check if project name matches exactly

#### Integration Issues
- **Journal Entry Creation Failed**: Verify account permissions and company settings
- **Project Status Not Updating**: Ensure project exists and user has Project permissions
- **Processing History Empty**: Check if any Investor Closing Vouchers have been submitted

### Troubleshooting Steps
1. **Clear Browser Cache**: `Ctrl+F5` or clear browser cache completely
2. **Clear Frappe Cache**: `bench clear-cache` on server
3. **Check Error Logs**: Review Frappe error logs for detailed error messages
4. **Verify Permissions**: Ensure user has required roles and permissions
5. **Database Integrity**: Run `bench migrate` to ensure all database changes applied

## 🏗️ Roadmap & Future Enhancements

### Recently Completed ✅
- ✅ **Account Reuse System**: Intelligent account reuse for same investor-project combinations
- ✅ **Investor Closing Voucher**: Complete dividend processing workflow
- ✅ **Duplicate Prevention**: Sophisticated validation prevents duplicate processing
- ✅ **Processing History**: Complete audit trail with detailed tracking
- ✅ **Project Status Automation**: Auto-completion when all investors processed
- ✅ **Manual Project Completion**: Force complete project for edge cases
- ✅ **Enhanced Error Handling**: Comprehensive validation and user feedback

### Upcoming Features 🚀
- [ ] **Investment Return Tracking**: Track actual returns vs projected returns
- [ ] **Advanced Dividend Calculations**: Support for tiered dividend structures
- [ ] **Bulk Import/Export**: Excel-based bulk investor and dividend processing
- [ ] **Mobile App Integration**: Mobile access for investment tracking
- [ ] **Advanced Analytics Dashboard**: Real-time investment and dividend analytics
- [ ] **API Endpoints**: REST API for external system integration
- [ ] **Investment Performance Metrics**: ROI, IRR, and other performance indicators
- [ ] **Automated Notifications**: Email notifications for investors and stakeholders
- [ ] **Multi-Company Consolidation**: Cross-company investment reporting
- [ ] **Investment Document Management**: Document storage and tracking per investment

### Version History
- **v1.0.0** (Initial): Basic investor management module
- **v1.1.0** (Q1 2025): Project integration and enhanced UI
- **v1.2.0** (Q1 2025): Automated accounting and sequential numbering
- **v1.3.0** (Q2 2025): Multi-currency support and exchange rate automation
- **v2.0.0** (Q3 2025): **Current** - Complete dividend processing and project automation
- **v2.1.0** (Q4 2025): Planned - Investment return tracking and advanced analytics

### Migration Notes
- **v1.x to v2.0**: Automatic migration with account reuse logic implementation
- **Database Changes**: New Investor Closing Voucher and Detail tables
- **Field Additions**: investor_id field added to child tables for duplicate prevention
- **Method Updates**: Enhanced server methods with improved error handling

## 📄 License

MIT License

Copyright (c) 2025 Gulf Energy Trading Company

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## 🎉 **Gulf Energy Investor Management System v2.0**

**A Complete Solution for Investment Lifecycle Management**

From initial investment tracking through dividend distribution to project completion - this system provides end-to-end automation with enterprise-grade reliability and audit capabilities.

**Built with ❤️ for Gulf Energy Trading Company**

*Powered by Frappe Framework & ERPNext*

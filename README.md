# Rewards Redemption Optimizer

A Streamlit-based application that helps travelers find the best value airline routes using miles vs cash payments. The tool analyzes flight data to recommend optimal redemption strategies for points and miles collectors. The tool helps users maximize the value of their rewards by comparing value per mile across different route options.

##  User Journey

1. **Arrive** at the application
2. **Pick** origin/destination airports and travel dates
3. **Choose** optimization objective ("maximize value" vs "minimum fees")
4. **Set** optional filters (price limits, airline preferences, miles balance)
5. **View** ranked results with value analysis
6. **Explore** interactive charts and optional map visualization
7. **Download** results as CSV for further analysis
8. **Leave** feedback to help improve the tool

## Features

### Core Functionality
- **Smart Route Search**: Find both direct flights and synthetic routes with layovers
- **Value Optimization**: Calculate value per mile to identify best redemption opportunities
- **Flexible Filtering**: Filter by price, airlines, and miles balance
- **Date Range Search**: Search across multiple dates in August 2025

### Visualizations
- **Comparison Charts**: Bar charts showing top routes by value per mile
- **Price vs Miles Scatter Plot**: Visualize the relationship between cost and miles required
- **Interactive Map**: Optional airport visualization (requires airports.csv)

### User Experience
- **Savings Calculator**: Shows estimated dollar savings for each route
- **Miles Balance Integration**: Filter routes based on your available miles
- **Modern UI**: Stripe-inspired dark theme with clean, accessible design
- **Export Functionality**: Download filtered results as CSV
- **Feedback System**: Submit suggestions and comments

⚠️ **Important**: For synthetic routing to work consistently, use LAX as the origin. Synthetic routes are most likely to be selected as best value with JFK or LHR destinations.

### Date Limitations
- **Supported Period**: August 2025 only (2025-08-01 to 2025-08-31)
- **August 31**: Direct flights only (no layover data available)
- **LHR Destinations**: Best results between August 2-26

### Missing Routes
The following route combinations do not exist in the database:
- DXB → LHR
- LHR → JFK

# Email Scraper Distributed

## Overview
This project is a **hierarchical distributed email address web scraper** designed to scrape email addresses from websites efficiently using a master-worker architecture with sub-nodes for maximum parallel processing. It's optimized for scraping large websites like [DLSU](https://www.dlsu.edu.ph) with unlimited scalability.

## Features
- **Hierarchical Distributed Architecture**: Master-worker model with sub-nodes for parallel processing
- **Unlimited Scalability**: No limit on number of workers - scale as needed
- **Batch Processing**: Efficient URL batch distribution to reduce network overhead
- **Sub-Node Parallelism**: Each worker uses multiple sub-nodes for concurrent scraping
- **Automatic Reconnection**: Workers automatically reconnect if disconnected
- **Performance Monitoring**: Detailed statistics and worker performance tracking
- **Smart Email Extraction**: Extracts emails from both HTML pages and PDF files
- **Contextual Information**: Extracts names, offices, and departments associated with emails
- **Statistics Export**: Saves scraping statistics to both console and text file
- **CSV Output**: Results saved in structured CSV format

## Project Structure
```
Web Scraper/
├── src/
│   ├── main.py                    # Entry point of the application
│   ├── scraper/
│   │   └── __init__.py           # Advanced scraper with PDF support
│   ├── distributed/
│   │   ├── master.py             # Master node with batch distribution
│   │   └── worker.py             # Worker nodes with sub-nodes
│   ├── utils/
│       └── __init__.py           # Utilities for logging and statistics
├── run_distributed_scraper.py    # Easy-to-use runner script
├── requirements.txt              # Project dependencies
├── scraped_emails.csv           # Output file (generated)
├── scraping_statistics.txt      # Statistics file (generated)
└── README.md                    # Project documentation
```

## Installation
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd email-scraper-distributed
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. (Optional) Install spaCy for enhanced name extraction:
   ```bash
   python -m spacy download en_core_web_sm
   ```

## Usage

### Option 1: Easy Runner Script (Recommended)
```bash
python run_distributed_scraper.py --urls "https://www.dlsu.edu.ph" --time 5 --workers 3 --sub-nodes 2
```

**Parameters:**
- `--urls`: Seed URLs to scrape (can specify multiple)
- `--time`: Time limit in minutes (default: 5)
- `--workers`: Number of workers to start initially (default: 3, unlimited supported)
- `--batch-size`: URLs per batch per worker (default: 3)
- `--sub-nodes`: Sub-nodes per worker for parallel processing (default: 2)
- `--port`: Master port (default: 5000)

### Option 2: Manual Execution

#### Start Master Node:
```bash
python -m src.distributed.master --urls "https://www.dlsu.edu.ph" --time 10 --batch-size 5
```

#### Start Worker Nodes (multiple terminals):
```bash
python -m src.distributed.worker --host localhost --port 5000 --sub-nodes 3
```

### Option 3: Legacy Single-Node Mode:
```bash
python src/main.py --urls "https://www.dlsu.edu.ph" --time 5
```

## Architecture

### Hierarchical Node Structure
```
Master Node (Unlimited Capacity)
├── URL Queue (batches)
├── Worker 1 (3 sub-nodes)
│   ├── Sub-node 1 → URL1, URL2, URL3
│   ├── Sub-node 2 → URL4, URL5, URL6  
│   └── Sub-node 3 → URL7, URL8, URL9
├── Worker 2 (3 sub-nodes)
│   ├── Sub-node 1 → URL10, URL11, URL12
│   ├── Sub-node 2 → URL13, URL14, URL15
│   └── Sub-node 3 → URL16, URL17, URL18
└── ... (unlimited workers)
```

### Key Components

#### Master Node
- **Batch Distribution**: Sends batches of URLs to workers
- **Dynamic Discovery**: Adds new discovered links to queue
- **Performance Tracking**: Monitors worker statistics
- **Unlimited Scaling**: Accepts unlimited worker connections

#### Worker Nodes
- **Sub-Node Parallelism**: Uses ThreadPoolExecutor for concurrent processing
- **Batch Processing**: Handles multiple URLs simultaneously
- **Automatic Reconnection**: Reconnects if disconnected
- **Link Discovery**: Finds and reports new links to master

#### Sub-Nodes
- **Parallel Scraping**: Each sub-node scrapes URLs independently
- **Error Handling**: Graceful error handling per URL
- **Performance Optimization**: Optimized for speed and efficiency

## Performance Examples

### High-Performance Setup
```bash
# 10 workers, 4 sub-nodes each = 40 parallel processing nodes
python run_distributed_scraper.py --urls "https://www.dlsu.edu.ph" --time 10 --workers 10 --sub-nodes 4 --batch-size 5
```

### Resource-Efficient Setup
```bash
# 3 workers, 2 sub-nodes each = 6 parallel processing nodes
python run_distributed_scraper.py --urls "https://www.dlsu.edu.ph" --time 5 --workers 3 --sub-nodes 2 --batch-size 3
```

### Single Machine Multi-Process
```bash
# Start master
python -m src.distributed.master --urls "https://www.dlsu.edu.ph" --time 10 --batch-size 5

# Start multiple workers in different terminals
python -m src.distributed.worker --host localhost --port 5000 --sub-nodes 3
python -m src.distributed.worker --host localhost --port 5000 --sub-nodes 3
python -m src.distributed.worker --host localhost --port 5000 --sub-nodes 3
```

## Output Files

### scraped_emails.csv
Contains scraped email data with columns:
- `email`: Email address
- `name`: Associated name (if found)
- `office`: Office/unit (if found)
- `department`: Department (if found)

### scraping_statistics.txt
Contains scraping statistics:
- Website URL
- Pages scraped
- Emails found
- Unique emails found

## Advanced Features

### PDF Support
- Automatically detects and scrapes PDF files
- Extracts text content and emails from PDFs
- Maintains context information

### Smart Name Extraction
- Uses spaCy NLP for intelligent name detection
- Regex-based fallback for name extraction
- Context-aware name association

### Fault Tolerance
- Workers automatically reconnect on disconnection
- Graceful error handling per URL
- No data loss on worker failures

### Performance Monitoring
- Real-time worker statistics
- Processing speed tracking
- Batch completion monitoring

# NSDSYST: Distributed Web-Scraper

## Project Structure

Master
├--Worker1
| ├--Task1 (url1)
| ├--Task2 (url2)
| ├--Task3 (url3)
| ├--Task4 (url4)
| ├--Taskn (urln)
├--Workern
| ├--Task1 (urln+1)
| ├--Task2 (urln+2)
| ├--Task3 (urln+3)
| ├--Task4 (urln+4)
| ├--Taskn (urln+5)

## Installing Dependencies

```
pip install aiohttp beautifulsoup4 lxml
```

## Running the Program

1. Run the Master.py code. Default options are already set. To show avaiable options you can append -h

```
python3 Master.py
```

2. On the same or separate machine, run the Worker.py. Make sure that the IP address of the Master.py indicated in the Worker.py source code matches.

```
python3 Worker.py
```

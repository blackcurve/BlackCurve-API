
# BlackCurve Python API Library 
<img alt='BlackCurve' src="https://i.ibb.co/T27MkzL/bc.png" width="250">

## API Documentation  
Documentation for the BlackCurve endpoints can be found [here](https://blackcurve.io/api/docs).  

## Requirements  
* Python 2.7+
* [Requests](http://docs.python-requests.org/en/master/) HTTP library for python v2.0 or above.  
  
## Installation
> `$ pip install blackcurve`

## Basic Usage
### Initiate a Connection
You just need your subdomain and a access token to get started
 ```python
	from blackcurve.api import BlackCurveAPI	
	bc = BlackCurveAPI({{ subdomain }}, {{ access_token }})	
```
### Reload a Access Token
Need a new access token, or just misplaced the old one?
 ```python
	bc = BlackCurveAPI({{ subdomain }})
	token = bc.get_access_token({{ client_key }}, {{ client_secret }})
	print(token)	
```
This will also update your BlackCurveAPI instance with the new token so you can immediately carry on with requests.

### Get Prices
Get a list of current Prices
 ```python
	# get all the prices
	bc.prices().all()
	
	# get all prices
	prices = bc.prices().all()
	print('You have {} prices'.format(len(prices)))
			
	# get a price for a single product by Product ID
	bc.prices().find('UK42')
	
	# filter specific product columns
	bc.prices(columns=['Price', 'Product ID']).all()
	
	# filter geography
	bc.prices(geography='UK').all()
	
	# filter by column value -- price >= 5
	bc.prices(price_gte=5).all()
	
```

### Data Sources Info
Get column and data type information about your data sources
 ```python
	# get all the data sources
	data_sources = bc.data_sources_info().all()
	print(data_sources)
	
	# get a single data source
	sales_history = bc.data_sources_info().find('Sales History')
	print(sales_history)
	
	# create a new column 
	sales_history['New Order Column'] = 'Integer'
	sales_history.save()
	
	# delete a column
	del sales_history['New Order Column']
	sales_history.save()
	
```
### Data Sources
Get a list of all of the data in a given source
 ```python
	# get all of the data from sales history
	bc.data_sources('Sales History').all()
	
	# get just the volume and product id columns in sales history
	bc.data_sources('Sales History', columns=['Volume', 'Product ID']).all()
	
	# filter by column value -- price >= 5
	bc.data_sources('Sales History', price_gte=5).all()
	
	# get a generator for all the pages returned in sales history (lazy requests)
	sales_history = bc.data_sources('Sales History').all()
	page = 1
	for x in sales_history:
		print('Page %s of Sales History: %s' % (page, x))
		page += 1
		
```

### Geographies & Currencies
Get a list of associated data for Geographies and Currencies
```python
    # get a list of all of the geography data
    all_geographies = bc.geographies().all()
    
    # get a specific geography
    website_uk = bc.geographies('Website UK').all()
    
    # get a list of all currencies
    all_currencies = bc.currencies().all()
    
```




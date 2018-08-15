from api.blackcurve_api import BlackCurveAPI

bc = BlackCurveAPI('health', 'eiheVY5qFnCe6xc9aA8qSTaBBrCqecSYtAfprfCCWEPFi58YsT')

# prices
prices = bc.prices()
all = prices.page(7)
item = prices.all()
print(item)

# data sources info
ds = bc.data_sources_info()
print(ds.all())
print(ds.find('Mohican'))

# data sources
df = bc.data_sources(columns=['id']).find('Mohican')
print

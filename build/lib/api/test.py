from api.blackcurve_api import BlackCurveAPI

bc = BlackCurveAPI('health', 'eiheVY5qFnCe6xc9aA8qSTaBBrCqecSYtAfprfCCWEPFi58YsT')
# bc = BlackCurveAPI('', 'eiheVY5qFnCe6xc9aA8qSTaBBrCqecSYtAfprfCCWEPFi58YsT')

# # prices
# prices = bc.prices()
# all = prices.page(7)
# item = prices.all()
# print(item)
#
# # data sources info
# ds = bc.data_sources_info()
# print(ds.all())
# print(ds.find('Mohican').page(1))

# data sources
df = bc.data_sources(date_gte='2018-01-01').find('Active Price History').page(1)

print(len(df['data']))

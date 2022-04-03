

file = 'config1'

x = 100

config = __import__(file)
globals()[config] = config

print(config.FILES)
print(config.X_LOC)
print(x)
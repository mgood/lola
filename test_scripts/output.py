import sys
print 'outputting'
sys.stdout.flush()
print >>sys.stderr, 'erroring'

from ufl import *

class Integral:
    def __init__(self, integrand, domain_type, domain_id, compiler_data, domain_data):

        self._domain_type = domain_type

        if isinstance(domain_id, int):
            self._domain_ids = (domain_id,)
        elif isinstance(domain_id, tuple):
            self._domain_ids = domain_id
        elif isinstance(domain_id, str):
            self._domain_ids = domain_id
        else:
            error

        self._integrand = integrand

        self._compiler_data = compiler_data
        self._domain_data = domain_data

    def restricted(self, domain_id):
        if self.domain_ids() == (domain_id,):
            return self
        else:
            return Integral(self.integrand(), self.domain_type(), domain_id, self.compiler_data(), self.domain_data())

    def annotated(self, compiler_data=None, domain_data=None):
        cd = self.compiler_data()
        sd = self.domain_data()
        if cd is compiler_data and sd is domain_data:
            return self
        else:
            if compiler_data is None:
                compiler_data = cd
            if domain_data is None:
                domain_data = sd
            return Integral(self.integrand(), self.domain_type(), self.domain_ids(), compiler_data, domain_data)

    def integrand(self):
        return self._integrand

    def domain_type(self):
        return self._domain_type

    def domain_ids(self):
        return self._domain_ids

    def compiler_data(self):
        return self._compiler_data

    def domain_data(self):
        return self._domain_data

    def __str__(self):
        return "I(%s, %s, %s, %s, %s)" % (self.integrand(), self.domain_type(), self.domain_ids(),
                                          self.compiler_data(), self.domain_data())

    def __repr__(self):
        return "Integral(%r, %r, %r, %r, %r)" % (self.integrand(), self.domain_type(), self.domain_ids(),
                                                 self.compiler_data(), self.domain_data())

def integral_domain_ids(integral):
    did = integral.measure.domain_id()
    if isinstance(did, int):
        return (did,)
    elif isinstance(did, tuple):
        return did
    elif isinstance(did, Region):
        return did.sub_domain_ids()
    elif isinstance(did, Domain):
        return Measure.DOMAIN_ID_EVERYWHERE
    elif isinstance(did, str):
        return did

# Mock objects for compiler data and solver data
comp1 = [1,2,3]
comp2 = ('a', 'b')
comp3 = {'1':1}
sol1 = (0,3,5)
sol2 = (0,3,7)

# Basic UFL expressions for integrands
V = FiniteElement("CG", triangle, 1)
f = Coefficient(V)
g = Coefficient(V)
h = Coefficient(V)

# FIXME: Replace these with real Integral objects
# Mock list of integral objects
integrals = {}
integrals["cell"] = [# Integrals over 0 with no compiler_data:
                     Integral(f, "cell", 0, None, None),
                     Integral(g, "cell", 0, None, sol1),
                     # Integrals over 0 with different compiler_data:
                     Integral(f**2, "cell", 0, comp1, None),
                     Integral(g**2, "cell", 0, comp2, None),
                     # Integrals over 1 with same compiler_data object:
                     Integral(f**3, "cell", 1, comp1, None),
                     Integral(g**3, "cell", 1, comp1, sol1),
                     # Integral over 0 and 1 with compiler_data object found in 0 but not 1 above:
                     Integral(f**4, "cell", (0,1), comp2, None),
                     # Integral over 0 and 1 with its own compiler_data object:
                     Integral(g**4, "cell", (0,1), comp3, None),
                     # Integral over 0 and 1 no compiler_data object:
                     Integral(h/3, "cell", (0,1), None, None),
                     # Integral over everywhere with no compiler data:
                     Integral(h/2, "cell", Measure.DOMAIN_ID_EVERYWHERE, None, None),
                     ]


### Algorithm sketch to build canonical data structure for integrals over subdomains

# Tuple comparison helper
from collections import defaultdict
from ufl.sorting import cmp_expr
from ufl.sorting import sorted_expr

class ExprTupleKey(object):
    __slots__ = ('x',)
    def __init__(self, x):
        self.x = x
    def __lt__(self, other):
        c = cmp_expr(self.x[0], other.x[0])
        if c < 0:
            return True
        elif c > 0:
            return self.x[1] < other.x[1]
        else:
            return False
def expr_tuple_key(expr):
    return ExprTupleKey(expr)

def integral_dict_to_sub_integral_data(integrals):
    # Data structures to return
    sub_integral_data = {}
    domain_data = {}

    # Iterate over domain types in order
    domain_types = ('cell',) # Measure._domain_types_tuple # TODO
    for dt in domain_types:
        # Get integrals list for this domain type if any
        itgs = integrals.get(dt)
        if itgs is not None:
            # Make canonical representation of integrals for this type of domain
            sub_integral_data[dt] = typed_integrals_to_sub_integral_data(itgs)

            # Get domain data object for this domain type and check that we found at most one
            domain_data[dt] = extract_domain_data_from_integrals(itgs)

    # Return result:
    #sub_integral_data[dt][did][:] = [(integrand0, compiler_data0), (integrand1, compiler_data1), ...]
    return sub_integral_data, domain_data

def build_sub_integral_list(itgs):
    sitgs = defaultdict(list)

    # Fill sitgs with lists of integrals sorted by and restricted to subdomain ids
    for itg in itgs:
        dids = itg.domain_ids()
        assert dids != Measure.DOMAIN_ID_OTHERWISE
        if dids == Measure.DOMAIN_ID_EVERYWHERE:
            # Everywhere integral
            sitgs[Measure.DOMAIN_ID_EVERYWHERE].append(itg)
        else:
            # Region or single subdomain id
            for did in dids:
                sitgs[did].append(itg.restricted(did)) # Restrict integral to this subdomain!

    # Add everywhere integrals to each single subdomain id integral list
    if Measure.DOMAIN_ID_EVERYWHERE in sitgs:
        # We'll consume everywhere integrals...
        ei = sitgs[Measure.DOMAIN_ID_EVERYWHERE]
        del sitgs[Measure.DOMAIN_ID_EVERYWHERE]
        # ... and produce otherwise integrals instead
        assert Measure.DOMAIN_ID_OTHERWISE not in sitgs
        sitgs[Measure.DOMAIN_ID_OTHERWISE] = []
        # Restrict everywhere integral to each subdomain and append to each integral list
        for did, itglist in sitgs.iteritems():
            for itg in ei:
                itglist.append(itg.restricted(did))
    return sitgs

def extract_domain_data_from_integrals(integrals):
    # Keep track of domain data objects, want only one
    ddids = set()
    domain_data = None
    for itg in integrals:
        dd = itg.domain_data()
        if dd is not None:
            domain_data = dd
            ddids.add(id(dd))
    assert len(ddids) <= 1, ("Found multiple domain data objects in form for domain type %s" % dt)
    return domain_data

def typed_integrals_to_sub_integral_data(itgs):
    # Make dict for this domain type with mapping (subdomain id -> integral list)
    sitgs = build_sub_integral_list(itgs)

    # Then finally make a canonical representation of integrals with only
    # one integral object for each compiler_data on each subdomain
    return canonicalize_sub_integral_data(sitgs)

def canonicalize_sub_integral_data(sitgs):
    for did in sitgs:
        # Group integrals by compiler data object id
        by_cdid = {}
        for itg in sitgs[did]:
            cd = itg.compiler_data()
            cdid = id(cd)
            if cdid in by_cdid:
                by_cdid[cdid][0].append(itg)
            else:
                by_cdid[cdid] = ([itg], cd)

        # Accumulate integrands separately for each compiler data object id
        for cdid in by_cdid:
            integrals, cd = by_cdid[cdid]
            # Ensure canonical sorting of more than two integrands
            integrands = sorted_expr((itg.integrand() for itg in integrals))
            integrands_sum = sum(integrands[1:], integrands[0])
            by_cdid[cdid] = (integrands_sum, cd)

        # Sort integrands canonically by integrand first then compiler data
        sitgs[did] = sorted(by_cdid.values(), key=expr_tuple_key)
        # E.g.:
        #sitgs[did][:] = [(integrand0, compiler_data0), (integrand1, compiler_data1), ...]

    return sitgs


# Print output for inspection:
def print_sub_integral_data(sub_integral_data):
    print
    for domain_type, domain_type_data in sub_integral_data.iteritems():
        print "======", domain_type
        for domain_id, sub_domain_integrands in domain_type_data.iteritems():
            print '---', domain_id,
            for integrand, compiler_data in sub_domain_integrands:
                print
                print "integrand:    ", integrand
                print "compiler data:", compiler_data

# Convert to integral_data format during transitional period:
def sub_integral_data_to_integral_data(sub_integral_data):
    integral_data = []
    for domain_type, domain_type_data in sub_integral_data.iteritems():
        for domain_id, sub_domain_integrands in domain_type_data.iteritems():
            integrals = [Integral(integrand, domain_type, domain_id, compiler_data, None)
                         for integrand, compiler_data in sub_domain_integrands]
            IntegralData = lambda *x: tuple(x) # TODO
            ida = IntegralData(domain_type, domain_id, integrals, {})
            integral_data.append(ida)
    return integral_data

# Run for testing and inspection
def test():

    sub_integral_data, domain_datas = integral_dict_to_sub_integral_data(integrals)

    print
    print "Domain data:"
    print domain_datas
    print

    print_sub_integral_data(sub_integral_data)

    integral_data = sub_integral_data_to_integral_data(sub_integral_data)

test()

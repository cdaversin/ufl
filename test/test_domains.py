#!/usr/bin/env python

"""
Tests of domain language and attaching domains to forms.
"""

# These are thin wrappers on top of unittest.TestCase and unittest.main
from ufltestcase import UflTestCase, main

# This imports everything external code will see from ufl
from ufl import *
from ufl.domains import as_domain
#from ufl.classes import ...
#from ufl.algorithms import ...

all_cells = (cell1D, cell2D, cell3D,
             interval, triangle, tetrahedron,
             quadrilateral, hexahedron)

class RegionConstructionTestCase(UflTestCase):

    def test_construct_domains_from_cells(self):
        for cell in all_cells:
            D1 = Domain(cell)
            D2 = as_domain(cell)
            self.assertFalse(D1 is D2)
            self.assertEqual(D1, D2)

    def test_as_domain_from_cell_is_unique(self):
        for cell in all_cells:
            D1 = as_domain(cell)
            D2 = as_domain(cell)
            self.assertTrue(D1 is D2)

    def test_construct_domains_with_names(self):
        for cell in all_cells:
            D2 = Domain(cell, name="D2")
            D3 = Domain(cell, name="D3")
            self.assertNotEqual(D2, D3)

    def test_domains_sort_by_name(self):
        # This ordering is rather arbitrary, but at least this shows sorting is working
        domains1 = [Domain(cell, "D%s"%cell.cellname()) for cell in all_cells]
        domains2 = [Domain(cell, "D%s"%cell.cellname()) for cell in sorted(all_cells)]
        sdomains = sorted(domains1)
        self.assertNotEqual(sdomains, domains1)
        self.assertEqual(sdomains, domains2)

    def test_topdomain_creation(self):
        D = Domain(triangle)

    def test_numbered_subdomains_are_registered(self):
        D = Domain(triangle)

        D1 = D[1]
        D2 = D[2]

        self.assertEqual(D.regions(), [D1, D2])
        self.assertEqual(D.region_names(), ['triangle_multiverse_1',
                                            'triangle_multiverse_2'])

    def test_named_subdomain_groups_are_registered(self):
        D = Domain(triangle)

        DL = Region(D, (1, 2), 'DL')
        DR = Region(D, (2, 3), 'DR')

        self.assertEqual(D.regions(), [DL, DR])
        self.assertEqual(D.region_names(), ['DL', 'DR'])

class MeasuresOverRegionsTestCase(UflTestCase):

    def setUp(self):
        UflTestCase.setUp(self)

        self.cell = tetrahedron
        self.D = Domain(self.cell)
        self.DL = Region(self.D, (1, 2), 'DL')
        self.DR = Region(self.D, (2, 3), 'DR')

    def test_construct_spaces_over_regions(self):
        VL = FiniteElement("CG", self.DL, 1)
        VR = FiniteElement("CG", self.DR, 1)
        self.assertNotEqual(VL, VR)
        self.assertEqual(VL.reconstruct(domain=self.DR), VR)
        self.assertEqual(VR.reconstruct(domain=self.DL), VL)
        #self.assertEqual(VL.region(), self.DL)
        #self.assertEqual(VR.region(), self.DR)

    def xtest_construct_measures_over_regions(self):
        VL = FiniteElement("CG", self.DL, 1)
        VR = FiniteElement("CG", self.DR, 1)
        self.assertNotEqual(Coefficient(VL, count=3), Coefficient(VR, count=3))
        self.assertEqual(Coefficient(VL, count=3), Coefficient(VL, count=3))
        fl = Coefficient(VL)
        fr = Coefficient(VR)

        # Three ways to construct an equivalent form
        M_dxr1 = fr*dx(self.DR) # FIXME: Make this pass
        M_dxr2 = fr*dx('DR')
        M_dx23 = fr*dx((2,3))
        self.assertEqual(M_dxr1, M_dx23)
        self.assertEqual(M_dxr1, M_dxr2)
        for M in (M_dxr1, M_dxr2, M_dx23):
            self.assertEqual(M.cell_integrals()[0].measure(), dx(self.DR))

        # Construct a slightly more complex form, including overlapping subdomains
        M1 = fl*dx(DL) + fr*dx(DR) # TODO: Test handling of legal measures
        M2 = fl*dx("DL") + fr*dx("DR") # TODO: Test regions by name
        M3 = fl*dx((1,2)) + fr*dx((2,3)) # TODO: Test subdomains by number
        M4 = fl*dx(1) + fl*dx(2) + fr*dx(2) + fr*dx(3) # TODO: Test subdomains by number

    def test_detection_of_coefficients_integrated_outside_support(self):
        pass
        #M = fl*dx(DR) + fr*dx(DL) # TODO: Test handling of illegal measures

    def test_extract_domains_from_form(self):
        cell = triangle
        # FIXME

    def test_(self):
        cell = triangle
        # FIXME

class FormDomainModelTestCase(UflTestCase):
    def test_form_domain_model(self):
        # Create domains with different celltypes
        DA = Domain(tetrahedron, 'DA') # TODO: Add something like this? , markers="arbitrary data")
        DB = Domain(hexahedron, 'DB')

        # Check python protocol behaviour
        self.assertNotEqual(DA, DB)
        self.assertEqual(set((DA,DA)), set((DA,)))
        self.assertEqual(set((DB,DB)), set((DB,)))
        self.assertEqual(set((DA,DB)), set((DB,DA)))
        self.assertEqual(sorted((DA,DB,DA,DB)), sorted((DB,DA,DA,DB)))

        # Check basic properties
        self.assertEqual(DA.name(), 'DA')
        self.assertEqual(DA.geometric_dimension(), 3)
        self.assertEqual(DA.topological_dimension(), 3)
        self.assertEqual(DA.cell(), tetrahedron)

        # Check region/domain getters
        self.assertEqual(DA.top_domain(), DA)
        self.assertEqual(DA.subdomain_ids(), None)
        self.assertEqual(DA.region_names(), [])
        self.assertEqual(DA.regions(), [])

        #BDA = Boundary(DA) # TODO
        #IDAB = Intersection(DA,DB) # TODO
        #ODAB = Overlap(DA,DB) # TODO

        # Create overlapping regions of each domain
        DAL = Region(DA, (1,2), "DAL")
        DAR = Region(DA, (2,3), "DAR")
        DBL = Region(DB, (0,1), "DBL")
        DBR = Region(DB, (1,4), "DBR")

        # Check that regions are available through domains
        self.assertEqual(DA.region_names(), ['DAL', 'DAR'])
        self.assertEqual(DA.regions(), [DAL, DAR])
        self.assertEqual(DA["DAR"], DAR)
        self.assertEqual(DA["DAL"], DAL)

        # Create function spaces on DA
        VA = FiniteElement("CG", DA, 1)
        VAL = FiniteElement("CG", DAL, 1)
        VAR = FiniteElement("CG", DAR, 1)

        # Create function spaces on DB
        VB = FiniteElement("CG", DB, 1)
        VBL = FiniteElement("CG", DBL, 1)
        VBR = FiniteElement("CG", DBR, 1)

        # TODO: Handle mixed spaces as well, butwant to get the basics sorted out first

        # Create functions in each space on DA
        fa = Coefficient(VA)
        fal = Coefficient(VAL)
        far = Coefficient(VAR)

        # Create functions in each space on DB
        fb = Coefficient(VB)
        fbl = Coefficient(VBL)
        fbr = Coefficient(VBR)

        # Create measure objects directly based on domain and region objects
        dxa = dx(DA)
        dxal = dx(DAL)
        dxar = dx('DAR') # Get Region by name

        # Create measure proxy objects from strings and ints, requiring
        # domains and regions to be part of their integrands
        dxb = dx('DB')   # Get Domain by name
        dxbl = dx(Region(DB, (1,4), 'DBL2')) # Provide a region with different name but same subdomain ids as DBL
        dxbr = dx((1,4)) # Assume unique Domain and provide subdomain ids explicitly

        # Create integrals on each region with matching spaces and measures
        Ma = fa*dxa
        Mar = far*dxar
        Mal = fal*dxal
        Mb = fb*dxb
        Mbr = fbr*dxbr
        Mbl = fbl*dxbl

        # TODO: How do we express the distinction between "everywhere" and "nowhere"? subdomain_ids=None vs []?

        # Create forms from integrals over overlapping regions on same top domain
        Marl = Mar + Mal
        Mbrl = Mbr + Mbl

        # Create forms from integrals over top domain and regions
        Mac = Ma + Marl
        Mbc = Mb + Mbrl

        # Create forms from separate top domains
        Mab = Ma + Mb

        # Create forms from separate top domains with overlapping regions
        Mabrl = Mac + Mbc

        #self.assertFalse(True) # Getting here, but it's not bloody likely that everything above is actually working. Add assertions!


class UnusedCases:
    def xtest_subdomain_stuff(self): # Old sketch, not working
        D = Domain(triangle)

        D1 = D[1]
        D2 = D[2]
        D3 = D[3]

        DL = Region(D, (D1, D2), 'DL')
        DR = Region(D, (D2, D3), 'DR')
        DM = Overlap(DL, DR)

        self.assertEqual(DM, D2)

        VL = VectorElement(DL, "CG", 1)
        VR = FiniteElement(DR, "CG", 2)
        V = VL*VR

        def sub_elements_on_subdomains(W):
            # Get from W: (already there)
            subelements = (VL, VR)
            # Get from W:
            subdomains = (D1, D2, D3)
            # Build in W:
            dom2elm = { D1: (VL,),
                        D2: (VL,VR),
                        D3: (VR,), }
            # Build in W:
            elm2dom = { VL: (D1,D2),
                        VR: (D2,D3) }

        # ElementSwitch represents joining of elements restricted to disjunct subdomains.

        # An element restricted to a domain union becomes a switch
        # of elements restricted to each disjoint subdomain
        VL_D1 = VectorElement(D1, "CG", 1)
        VL_D2 = VectorElement(D2, "CG", 1)
        VLalt = ElementSwitch({D1: VL_D1,
                               D2: VL_D2})
        # Ditto
        VR_D2 = FiniteElement(D2, "CG", 2)
        VR_D3 = FiniteElement(D3, "CG", 2)
        VRalt = ElementSwitch({D2: VR_D2,
                               D3: VR_D3})
        # A mixed element of ElementSwitches is mixed only on the overlapping domains:
        Valt1 = VLalt*VRalt
        Valt2 = ElementSwitch({D1: VL_D1,
                               D2: VL_D2*VR_D2,
                               D3: VR_D3})

        ul, ur = TrialFunctions(V)
        vl, vr = TestFunctions(V)

        # Implemented by user:
        al = dot(ul,vl)*dx(DL)
        ar = ur*vr*dx(DR)

        # Disjunctified by UFL:
        alonly = dot(ul,vl)*dx(D1) # integral_1 knows that only subelement VL is active
        am = (dot(ul,vl) + ur*vr)*dx(D2) # integral_2 knows that both subelements are active
        aronly = ur*vr*dx(D3) # integral_3 knows that only subelement VR is active

# Don't touch these lines, they allow you to run this file directly
if __name__ == "__main__":
    main()

"""
This module defines two coherence models:
nwtc - The NWTC 'non-IEC' coherence model.
iec  - The IEC coherence model.
"""
from mBase import cohModelBase,np,ts_float,tslib,dbg
from ..misc import Lambda

class nwtc(cohModelBase):
    """
    The NWTC 'non-IEC' coherence model for velocity component 'k' (u,v,w) between two
    points (z_i,y_i) and (z_j,y_j) is:

       Coh_k=exp(-a_k*(r/z_m)*CohExp*((f*r/u_m)**2+(b_k*r)**2))

    Where:
      f is frequency.
      r is the distance between the two points.
      a_k and b_k are 'coherence decrement' input parameters for each of the
          velocity components.
      u_m is the average velocity of the two points.
      z_m is the average height of the two points.
      CohExp is the 'coherence exponent' input parameter (default is 0).
    """
    __doc__+=cohModelBase.__doc__

    def __init__(self,a=[None,None,None],b=[0.,0.,0.],CohExp=0.0):
        """
        Create a NWTC 'non-IEC' coherence model.
        
        Parameters
        ----------
        a : 3-element array-like of floats (or None for default), optional.
            The first coherence decrement input parameter for each of the
            three velocity components. If an element is None, a default value
            is used. The defaults are:
                 a[0] = uhub
                 a[1] = 0.75*a[0]
                 a[2] = 0.75*a[0]
        b : 3-element array-like of floats, optional.
            The second coherence decrement input parameter for each velocity component.
            Each element defaults to 0.
        CohExp :  float, optional
        """
        if CohExp is None:
            self.CohExp=0.0
        else:
            self.CohExp=CohExp
        self.a=a
        self.b=b
        if dbg:
            self.timer=dbg.timer('tslib-cohNWTC')
        
    def init_cohi(self,cohi):
        """
        This method is called (if it exists) by the coherence model __call__ method
        just before returning the coherence instance *cohi*.
        """
        cohi.a=np.empty((3),dtype=ts_float)
        cohi.b=np.array(self.b,dtype=ts_float)
        if self.a[0] is None:
            cohi.a[0]=cohi.prof.uhub
        else:
            cohi.a[0] = self.a[0]
        if self.a[1] is None:
            cohi.a[1] = 0.75*cohi.a[0]
        else:
            cohi.a[1]=self.a[1]
        if self.a[2] is None:
            cohi.a[2]=0.75*cohi.a[0]
        else:
            cohi.a[2]=self.a[2]
        cohi.CohExp=self.CohExp
 
    def calc(self,cohi,comp):
        """
        
        """
        if tslib is not None:
            if dbg:
                self.timer.start()
            #cohi[:]=tslib.nonieccoh(cohi.spec.flat[comp],cohi.f,cohi.grid.y,cohi.grid.z,cohi.grid.flatten(cohi.prof.u),cohi.a[comp],cohi.b[comp],self.CohExp,cohi.ncore,cohi.n_f,cohi.n_y,cohi.n_z)
            tslib.nonieccoh(cohi._crossSpec,cohi.f,cohi.grid.y,cohi.grid.z,cohi.grid.flatten(cohi.prof.u),cohi.a[comp],cohi.b[comp],self.CohExp,cohi.ncore,cohi.n_f,cohi.n_y,cohi.n_z)
            if dbg:
                self.timer.stop()
        else:
            cohModelBase.calc(self,cohi,comp)

    def calcCoh(self,cohi,comp,ii,jj):
        """
        The base function for calculating coherence for non-IEC spectral models.

        See the TurbSim documentation for further information.

        This function is only used if the TSlib fortran library is not available.
        """
        r=cohi.grid.dist(ii,jj)
        two=ts_float(2)
        zm=(cohi.grid.z[ii[1]]+cohi.grid.z[jj[1]])/two
        um=(cohi.prof.u[ii]+cohi.prof.u[jj])/two
        return np.exp(-cohi.a[comp]*(r/zm)**self.CohExp*np.sqrt((cohi.f*r/um)**two+(cohi.b[comp])**two))
    

class iec(cohModelBase):
    """
    The 'IEC' coherence model for the u velocity component between two
    points (z_i,y_i) and (z_j,y_j) is:

       Coh=exp(-a*((f*r/uhub)^2+(0.12*r/Lc)^2)^0.5)

    The IEC coherence is zero for the v and w components (coherence matrix
    is the identity matrix so that auto-spectra are retained).
    
    Where:
      f is frequency.
      r is the distance between the two points.
      uhub is the hub-height mean velocity.
      a and Lc are constants according to,
        If IECedition<=2:
          a  = 8.8
          Lc = 2.45*min(30m,HubHt)
        If IECedition>=3:
          a  = 12
          Lc = 5.67*min(60m,HubHt)
    """
    __doc__+=cohModelBase.__doc__

    def _L(self,zhub):
        """
        Calculate the 'coherence scale parameter' for hub-height *zhub*.
        """
        return self._Lfactor*Lambda(zhub,self.IECedition)
    
    def __init__(self,IECedition=3):
        """
        Create an IEC spectral model object.

        Parameters
        ----------
        IECedition - int (2 or 3),
                     Different IEC editions have slightly different coefficients to the
                     spectral model.
        """
        self.IECedition=IECedition
        if IECedition<=2:
            self._Lfactor=3.5 # The Lambda function includes a factor of 0.7 (_Lfactor*0.7=2.45).
            self.a=8.8
        else: # 3rd edition IEC standard:
            self._Lfactor=8.1 # The Lambda function includes a factor of 0.7 (_Lfactor*0.7=5.67)
            self.a=12.
        if dbg:
            self.timer=dbg.timer('tslib-cohIEC')

    def init_cohi(self,cohi):
        """
        Initialize a coherence instance for the IEC coherence model.
        """
        cohi.Lc=self._L(cohi.grid.zhub)

    def calc(self,cohi,comp):
        """
        Compute and set the full cross-spectral matrix for component *comp* for 'coherence calculator' instance *cohi*.
        
        Compute the coherence array for coherence instance cohi for the IEC model.
        
        """
        #
        if comp!=0:
            cohi[:]=0 # Set all elements to zero.
            cohi[cohi._i_diag]=cohi.spec.flat[comp] # Set the diagonal elements to be the spectra:
            cohi._crossSpec_name=comp
        elif tslib is not None:
            if dbg:
                self.timer.start()
            cohi[:]=tslib.ieccoh(cohi._crossSpec,cohi.f,cohi.y,cohi.z,cohi.prof.uhub,self.a,cohi.Lc(cohi.grid.zhub),cohi.ncore,cohi.n_f,cohi.n_y,cohi.n_z)
            if dbg:
                self.timer.start()
        else:
            cohi[:]=cohModelBase.calc(self,cohi,comp)
        
    def calcCoh(self,cohi,comp,ii,jj):
        """
        Calculate the *comp* (0, 1 or 2) coherence between points *ii*=(iz,iy) and *jj*=(jz,jy) for the IEC model.

        This method is only used if tslib is not available.
        
        Parameters
        ----------
        *cohi*    - A 'coherence calculator' instance (for the given tsrun).
        *comp*    - an integer (0,1,2) indicating the velocity component for which to compute the coherence.
        *ii*,*jj* - Two-integer elements indicating the grid-points between which to calculate the coherence.
                    for example: ii=(1,3),jj=(2,3)
                    
        """
        if comp==0:
            r=cohi.grid.dist(ii,jj)
            return np.exp(-self.a*np.sqrt((cohi.f*r/cohi.prof.uhub)**2+(0.12*r/cohi.Lc(cohi.grid.zhub))**2))
        else:
            return 0
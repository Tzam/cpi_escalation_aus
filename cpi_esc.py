import datetime
import pandas as pd
import numpy as np
from pathlib import Path

CPITABLELOC = Path(__file__)/'../cpi_2019-09-01.csv'
 
#cpidata = pd.read_excel(CPITABLELOC,parse_dates=['Date'],dayfirst=True)

class CpiEscalator():
    """Class to handle escalation calculations. target date is a 'real' basis that nominal values can be converted to.
    Call the class as a function after initialisation for nominal to real conversion, or use the .to_real() and .to_nominal() methods
    """
    
    def __init__(self, cpidata:pd.DataFrame, target_date: datetime.datetime = None, future_escalation:float = 1.025,
                 allow_estimation:bool = True):
        
        #check that the format of the cpidata passed makes sense, and ensure we have consitent column names
        if cpidata.shape[1] != 2:
            raise ValueError('cpidata should be a pandas datafame with 2 columns, one with datetimes and the other numeric')
        try:
            self.cpidata = (pd.DataFrame(data={'Date':cpidata.select_dtypes(include=['datetime']).iloc[:,0],
                                              'CPI':cpidata.select_dtypes(include=['number']).iloc[:,0]})
                            .sort_values(by=['Date'])
                           )
        except:
            raise ValueError('cpidata should be a pandas datafame with 2 columns, one with datetimes and the other numeric')
        
        self._minrefdate = self.cpidata['Date'].min()
        self._maxrefdate = self.cpidata['Date'].max()
        self._default_esc = future_escalation
        self.allow_estimation = allow_estimation
        
        #convert target date to a date type
        if not target_date:
            target_date = datetime.datetime.today()
        self.set_target_date(target_date)
        
        #factors are expressed so that nominal * factor -> real
        self._recalculate_cpi_factors()
        
        
        
    def __call__(self,dates:pd.Series, values:pd.Series):
        return self.to_real(dates,values)
    
    def _recalculate_cpi_factors(self):
        #finds the index of the last date in the cpi dataset which is smaller than the target date 
        target_cpi = self.cpidata['CPI'][(self.cpidata['Date']<=self.target_date).to_numpy().nonzero()[0][-1]]
        self.cpidata['cpi_esc_factor'] = target_cpi / self.cpidata['CPI']
    
    def _get_estimated(self,dates:pd.Series, values:pd.Series):
        #account for times outside the range
        dates = pd.to_datetime(dates)
        
        if (dates.min() < self._minrefdate or dates.max() > self._minrefdate) and (not self.allow_estimation):
            raise ValueError("All dates must be within historic cpi ranges when 'allow_estimation' = False")
            
        
        data = pd.DataFrame({'date':dates,'value':values})
        
        lowers = data[data['date']<self._minrefdate].copy()
        uppers = data[data['date']>self._maxrefdate].copy()
        withins = data[np.logical_and(data['date']>=self._minrefdate,data['date']<=self._maxrefdate)].copy()
        
        if not lowers.empty:
            lowers['esc_factor'] = self._get_estimated_esc(lowers['date'],self._minrefdate)
        if not uppers.empty:
            uppers['esc_factor'] = self._get_estimated_esc(uppers['date'],self._maxrefdate)
        
        if not withins.empty:
            within_idxs = np.searchsorted(self.cpidata['Date'],withins['date'])
            withins['esc_factor'] = self.cpidata['cpi_esc_factor'][within_idxs].to_numpy()
        
        data = pd.concat([lowers,uppers,withins],sort=True).sort_index()
        return data
    
    def _get_estimated_esc(self, outside_dates,refdate):
        yrsahead = outside_dates.sub(refdate).map(lambda td: td.days / 365.25).to_numpy()
        refcpi= self.cpidata['cpi_esc_factor'][self.cpidata['Date']==refdate].to_numpy()
        outside_factors = np.array(np.power(self._default_esc,-yrsahead)*refcpi)
        return outside_factors
    
    @classmethod
    def from_csv(cls, path = None, target_date: datetime.datetime = None, future_escalation:float = 1.025,
                 allow_estimation:bool = True, **kwargs) -> object:
        """**kwargs are passed to the pd.read_csv method. If you don't specify path, parse_dates and dayfirst arguments I assume some defaults
        to prevent errors in the default path"""

        if not path:
            path = str(CPITABLELOC)
            try:
                parse_dates = kwargs.pop('parse_dates')
            except:
                parse_dates = ['Date']
            try:
                dayfirst = kwargs.pop('dayfirst')
            except:
                dayfirst = True

        cpidata = pd.read_csv(path,parse_dates = parse_dates, dayfirst=dayfirst, **kwargs)
        return cls(cpidata,target_date,future_escalation,allow_estimation)

    
    def set_target_date(self,target_date) -> None:
        if type(target_date)=='datetime.date':
            target_date = datetime.datetime.combine(target_date,datetime.time())
        
        self.target_date = pd.Timestamp(target_date)
        self._recalculate_cpi_factors()
        
    def to_real(self,dates:pd.Series, values:pd.Series) -> pd.Series:
        """Converts a series of 'values' from nominal to real, using 'dates' as cpi references"""
        data = self._get_estimated(dates,values)
        
        return data['value'] * data['esc_factor']
    
    def to_nominal(self,dates:pd.Series, values:pd.Series) -> pd.Series:
        """Converts a series of 'values' from real to nominal, using 'dates' as cpi references"""
        data = self._get_estimated(dates,values)
        
        return data['value'] / data['esc_factor']
        

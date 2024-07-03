
import pandas as pd
import ipywidgets as widgets
import numpy as np
from IPython.display import display
from df_functions import *

cc = CostCalculator()
cc.read_from_xlsx('amc_menu_database.xlsx')
nicks = set(cc.uni_g['nickname'].dropna().unique())
ingrs = set(cc.costdf['ingredient'].dropna().unique())
allvals = nicks.union(ingrs)

def parse_quantity(quant):
    quant = quant.replace('ct', 'count')
    try:
        quant = Q_(quant)
    except:
        quant = None
    return quant
            

class DataFrameWidget:
    ''' ipywidgets based interactive interface for pandas
    '''
    
    def __init__(self, df, width='80px', enabled_columns=None, hide_columns=None, 
                 cc=CostCalculator(), output=widgets.Output(), trigger=None):
        self.df = df.reset_index(drop=True).copy()
        self.defcolor = widgets.Text().style.text_color
        self.width = width
        self.column_width = {}
        self.df_type = None
        self.enabled_columns = enabled_columns if enabled_columns else []
        self.hide_columns = hide_columns if hide_columns else []
        self.cc = cc
        nicks = set(cc.uni_g['nickname'].dropna().unique())
        ingrs = set(cc.costdf['ingredient'].dropna().unique())
        self.all_ingredients = nicks.union(ingrs)
        self.buttons = {}
        self.output = output #widgets.Output()  # Create an output widget to display the grid
        self.num_cols = 0
        self.trigger = trigger
        self.last_lookup = ''
        self.cost_multipliers = [3.0, 3.5]
        # self.findtype()
        if self.df.empty:
            self.df_type = None
        elif 'ingredient' in self.df.columns and len(self.df['ingredient'].dropna().unique()) == 1:
            self.df_type = 'mentions'
        elif 'nickname' in self.df.columns:
            self.df_type = 'guide'
        elif 'ingredient' in self.df.columns:
            self.df_type = 'recipe'
        else:
            self.df_type = None
            
        self.df_types = set(('guide', 'recipe', 'mentions'))
        
        self.grid = self._create_grid()

    def setdf(self, mylookup):
        self.last_lookup = mylookup
        mydf =  self.cc.findframe(mylookup).reset_index(drop=True).copy()
        self.df = mydf
        self.findtype()
        if (self.df_type == 'recipe'):
            colorder = ['item', 'ingredient', 'quantity', 'cost', 'equ quant']
            mydf = reorder_columns(mydf, colorder)
            mycolumns = [x for x in mydf.columns if x not in self.hide_columns]
            mydf = mydf[mycolumns]
            for cm in self.cost_multipliers:
                if cm > 0:
                    add_costx(mydf, cm)
            if 'menu price' in mydf.columns and len(self.cost_multipliers) > 0:
                add_netprofit(mydf, self.cost_multipliers[0])
            self.df = mydf
            self.update_column_width()
        else:
            mycolumns = mydf.columns
            if (self.df_type == 'guide'):
                mycolumns = [x for x in mydf.columns if x not in ['myconversion', 'mycost']]
            else:
                mycolumns =  [x for x in mydf.columns if x not in self.hide_columns]
            mydf = mydf[mycolumns]
            self.df = mydf
            self.update_column_width()
            
            
    def update_column_width(self):
        def carlen(myval):
            myval = f"{myval:0.2f}" if isinstance(myval, float) else myval
            return len(str(myval))

        # Calculate maxlen using map
        try:
            maxlen = self.df.apply(lambda x: x.map(lambda y: 5 + 10 * carlen(y))).max().to_dict()
        except:
            maxlen = self.width

        # Calculate cn_len for column names
        cn_len = {c: 5 + 8 * len(str(c)) for c in self.df.columns}

        # Update column_width using the maximum value between maxlen and cn_len
        self.column_width = {c: max(maxlen[c], cn_len[c]) for c in maxlen}
        if self.df_type == 'recipe':
            self.column_width['item'] = 5 + 8 * len('recipe for:')

    def update_column_width2(self):
        def carlen(myval):
            myval = f"{myval:0.2f}" if isinstance(myval, float) else myval
            return len(str(myval))
    
        # Calculate maxlen using applymap
        try:
            maxlen = self.df.applymap(lambda x: 5 + 10 * carlen(x)).max().to_dict()
        except:
            maxlen = self.width
    
        # Calculate cn_len for column names
        cn_len = {c: 5 + 8 * len(str(c)) for c in self.df.columns}
    
        # Update column_width using the maximum value between maxlen and cn_len
        self.column_width = {c: max(maxlen[c], cn_len[c]) for c in maxlen}
        if self.df_type == 'recipe':
            self.column_width['item'] = 5+8*len('recipe for:')

        
    def update_display(self):
        self.grid.disabled = True
        self.grid = self._create_grid()
        with self.output:
            self.output.clear_output(wait=True)
            display(self.grid)

        if (self.trigger != None):
            if (self.df_type == 'recipe'):
                self.trigger(self.df.iloc[0]['ingredient'])
            elif (self.df_type == 'guide'):
                self.trigger(self.df.loc[0]['nickname'])

            
    def getlayout(self, col=None):
        if col and col in self.column_width:
            return {'width': f"{self.column_width[col]}px", 'padding': '0px 1px'}
        else:
            return {'width': self.width, 'padding': '0px 1px'}
        
    def findtype(self):
        if self.df.empty:
            self.df_type = None
        elif 'ingredient' in self.df.columns:
            if self.df.iloc[0]['item'] == 'recipe':
                self.df_type = 'recipe'                
            else:
                self.df_type = 'mentions'
        elif 'nickname' in self.df.columns:
            self.df_type = 'guide'
        else:
            self.df_type = None
            
        return self.df_type
        
    def _create_grid(self):
        # Create a list to store the widgets
        items = []
        
        self.num_cols = len(self.df.columns) + 1 # extra one for button
        # Create a GridBox to display the widgets

        # Setup column names
        # add blank label in place of a button
        
        for i in range(self.num_cols - len(self.df.columns)):
            items.append(widgets.Label(value='', layout=self.getlayout()))
        
        # add column labels for each column at top of interface
        for col in self.df.columns:
            items.append(widgets.Label(value=col, layout=self.getlayout(col)))
            
        # if we have a recipe df, add row at end for ability to add to ingredient to recipe
        if self.df_type == 'recipe':
            new_row = pd.DataFrame({column: [''] for column in self.df.columns})
            # set blank row up as a member of the recipe
            new_row['item'] = self.df.iloc[0]['ingredient']
            self.df = pd.concat([self.df, new_row], ignore_index=True)

        # Create interface for each row of the DataFrame
        for index, row in self.df.iterrows():
            self.create_row(items, index, row)
        
        grid = widgets.GridBox(items, layout=widgets.Layout(grid_template_columns=f"repeat({self.num_cols}, {self.width})"))
        # set the width of the first column to 100 pixels
        grid.layout.grid_template_columns = f"{self.width} {'px '.join([str(self.column_width[x]) for x in self.df.columns])}px"
        return grid
    
    def create_row(self, items, index, row):
        ''' given a 'row' from a dataframe and the 'index' of the row in the dataframe
            create ui widgets for the row and add the widgets to 'items'
        '''
        # Create a button for each row and associate it with the row index
        # only create lookup button for row with ingredients
        #if self.df_type == 'recipe' and row['item'] != 'recipe':
        butlist = []
        
        def create_lookup_button():
            # check there is a valid thing to lookup
            button = widgets.Button(description=f'lookup', layout=self.getlayout())
            if self.cc.findframe(row['ingredient']).empty:
                button.disabled = True
            button.tag = index  # Store the row index in the button's 'tag' attribute
            button.on_click(self.on_lookup_click)
            return button
        
        def create_search_button():
            button = widgets.Button(description=f'search', layout=self.getlayout())
            button.tag = index  # Store the row index in the button's 'tag' attribute
            button.on_click(self.on_search_click)
            return button

        def create_duplicate_button():
            button = widgets.Button(description=f'duplicate', layout=self.getlayout(), button_style='info')
            button.tag = index  # Store the row index in the button's 'tag' attribute
            button.on_click(self.on_duplicate_click)
            return button
        
        def set_df_val(df, row, column, newval):
            df.loc[
                (
                    df['item'] == row['item']
                ) & 
                (
                    df['ingredient'] == row['ingredient']
                ), column] = newval

        def set_df_for_iq(df, row, column, newval):
            '''
                set a value for df, match ingredient, quantity
            '''
            df.loc[
                (
                    df['ingredient'] == row['ingredient']
                ) & 
                (
                    df['quantity'] == row['quantity']
                ), column] = newval
            
        def get_df_val(df, row, column):
            return df.loc[
                (
                    df['item'] == row['item']
                ) & 
                (
                    df['ingredient'] == row['ingredient']
                ), column].values[0]

            
        # Add an observer to the Text widget that enables the button when the content changes
        def on_text_change(change, column, widget):
            
            def _update_df(df, row, match_columns, update_column, new_value):
                condition = True
                for col in match_columns:
                    condition &= (df[col] == row[col])
                df.loc[condition, update_column] = new_value
                
            # clear cost of each recipe containing ingredient
            def _clear_costs(nickname):
                mdf = self.cc.find_ingredient(nickname)
                for i,m in mdf.iterrows():
                    self.cc.set_item_ingredient(m['item'], nickname, 'cost', 0)
                    self.cc.clear_cost(m['item'])
            
            defmatch = ['nickname', 'description', 'size', 'price', 'date', 'supplier']
            newval = change['new']
            oldval = self.df.iloc[index][column]
                
            if column == 'quantity':
                if self.df_type == 'recipe':
                    recipename = self.df.iloc[0]['ingredient']
                    # only update as recipe if in recipe mode
                    # check that we are editting a quantity for a valid ingredient
                    if self.df.iloc[index]['ingredient'] in self.all_ingredients:
                        newsize = parse_quant(newval)
                        oldsize = parse_quantity(oldval)
                        # print(f"{oldval=}, {newval=}")
                        row = self.df.iloc[index]
                        # set_df_val(cc.costdf, row, column, newval)
                        self.df.loc[index:index, column] = newval
                        if (newval != oldval):
    
                            #button[0].disabled = False
                            updatecost = True
                            set_df_val(self.cc.costdf, row, column, newval)
                            set_df_val(self.cc.costdf, row, 'cost', 0)
    
                            self.cc.clear_cost(recipename)
                            self.cc.recipe_cost(recipename)
                            self.setdf(recipename)
                            self.update_display()
                        
            elif column == 'ingredient':
                if self.df_type == 'recipe':
                    recipename = self.df.iloc[0]['ingredient']
                    # check if valid ingredient
                    if newval in self.all_ingredients:
                        widget.style.text_color = self.defcolor
                        # check if ingredient is alread in recipe
                        self.df.loc[index:index, 'item'] = recipename
                        if newval in self.cc.item_list(recipename)['ingredient'].unique():
                            # ignore (repeated ingredients not allowed)
                            print('already in recipe')
                        else:
                            # check if there was a valid old value
                            if oldval in self.all_ingredients:
                                self.cc.removeIngredient(recipename, oldval)

                            # add new row to costdf
                            # set quantity to zero if none
                            self.df.loc[index:index, 'ingredient'] = newval
                            quant = parse_quant(self.df.loc[index]['quantity'])
                            if not quant:
                                self.df.loc[index:index, 'quantity'] = '0'
                            self.df.loc[index:index, 'cost'] = 0
                            newdf = pd.DataFrame([self.df.iloc[index]])
                            self.cc.costdf = pd.concat([self.cc.costdf, newdf], ignore_index=True)

                            self.cc.clear_cost(recipename)
                            self.cc.recipe_cost(recipename)
                            self.setdf(recipename)
                            # self.df = self.cc.findframe(reciperow['ingredient']).reset_index(drop=True)
                            self.update_display()

                    else: # newval not an ingredient
                        if str(newval) == '':
                            self.cc.removeIngredient(recipename, oldval)
                            self.cc.clear_cost(recipename)
                            self.cc.recipe_cost(recipename)
                            self.setdf(recipename)
                            # self.df = self.cc.findframe(reciperow['ingredient']).reset_index(drop=True)
                            self.update_display()
                        else:
                            widget.style.text_color = 'red'
                            #widget.add_class('invalid-input')  # CSS class for invalid input

                            

            elif column == 'saved cost':
                # check if valid cost
                try:
                    newval = float(newval)
                    # check valid value
            
                except:
                    # clear saved cost?
                    newval = -1

                if self.df_type == 'recipe':
                    recipename = self.df.iloc[0]['ingredient']
                    # update saved cost
                    row = self.df.iloc[index]
                    if (newval < 0):
                        set_df_val(self.cc.costdf, row, 'saved cost', np.nan)
                        if (cc.use_saved):
                            self.cc.set_item_ingredient(recipename, row['ingredient'], 'cost', 0)
                            self.cc.costdf.loc[self.cc.costdf['ingredient'] == row['ingredient'],'cost'] = 0
                    else:
                        set_df_val(self.cc.costdf, row, 'saved cost', newval)
                    #set_df_val(cc.costdf, row, 'cost', newval)
                    
                    # zero out all affected cost
                    # parent recipe, 
                    self.cc.clear_cost(recipename)

                    self.cc.recipe_cost(recipename)
                    self.setdf(recipename)
                    print('saved cost')
                    self.update_display()
                    
            elif column == 'menu price':
                # check if valid cost
                try:
                    newval = float(newval)
                    # check valid value
            
                except:
                    print('invalid menu price')
                    return

                if self.df_type == 'recipe':
                    recipename = self.df.iloc[0]['ingredient']
                    # update menu price
                    row = self.df.iloc[index]
                    #self.cc.costdf.loc[self.costdf['']
                    set_df_for_iq(self.cc.costdf, row, 'menu price', newval)
                    self.setdf(recipename)
                    self.update_display()

            elif column == 'date':
                if self.df_type == 'guide':
                    row = self.df.iloc[index]
                    # match nickname, description, size, date
                    mydate = pd.to_datetime(newval, errors='coerce')
                    if (mydate is pd.NaT):
                        # don't update if date if the input is invalid
                        self.update_display()
                    else:
                        mydate = mydate.strftime('%Y-%m-%d')
                        
                        _update_df(self.cc.uni_g, row, defmatch, 'date', mydate)
                        
                        _clear_costs(row['nickname'])

                        self.setdf(row['nickname'])
                        self.update_display()
                    
            elif column == 'size':
                if self.df_type == 'guide':
                    row = self.df.iloc[index]
                    newval = newval.strip()
                    newsize = parse_size(newval)
                    if (newval in ['', '-', '0']) or (newsize.m <= 0):
                        # ignore blank size, 0 size
                        self.update_display()
                    else:
                        # match nickname, description, size, date
                        _update_df(self.cc.uni_g, row, defmatch, 'size', newval)
                        _clear_costs(row['nickname'])
    
                        self.setdf(row['nickname'])
                        self.update_display()
                        # update mention display?
            
            elif column == 'price':
                if self.df_type == 'guide':
                    row = self.df.iloc[index]
                    try:
                        newval = float(newval)
                    except:
                        print('bad new price')
                        return

                    # match nickname, description, size, date, and update
                    _update_df(self.cc.uni_g, row, defmatch, 'price', newval)
                    
                    # clear cost of each recipe containing ingredient
                    _clear_costs(row['nickname'])

                    self.setdf(row['nickname'])
                    self.update_display()
                    # update mention display?
                    
            elif column == 'supplier':
                if self.df_type == 'guide':
                    row = self.df.iloc[index]
                    # match nickname, description, size, date, and update
                    _update_df(self.cc.uni_g, row, defmatch, 'supplier', newval)          
                    # clear cost of each recipe containing ingredient
                    _clear_costs(row['nickname'])

                    self.setdf(row['nickname'])
                    self.update_display()
                    # update mention display?
                    
            elif column == 'description':
                if self.df_type == 'guide':
                    row = self.df.iloc[index]
                    # match nickname, description, size, date, and update
                    _update_df(self.cc.uni_g, row, defmatch, 'description', newval)          
                    self.setdf(row['nickname'])
                    self.update_display()
                    # update mention display?
                    
            elif column == 'allergen':
                if self.df_type == 'guide':
                    row = self.df.iloc[index]
                    # match nickname, description, supplier
                    _update_df(self.cc.uni_g, row, ['nickname', 'description', 'supplier'], 'allergen', newval)          
                    self.setdf(row['nickname'])
                    self.update_display()
                    # update mention display?
                    
            elif column == 'conversion':
                if self.df_type == 'guide':
                    row = self.df.iloc[index]
                    newval = newval.strip()
                    # check valid conversion
                    convrs = parse_conversion(newval)
                    if len(convrs) > 0:
                        # set convrs
                        _update_df(self.cc.uni_g, row, ['nickname', 'description', 'size', 'supplier'], 'conversion', newval)
                        _clear_costs(row['nickname'])
                        self.setdf(row['nickname'])
                        self.update_display()
        
        # add button based on what type of dataframe we have
        if self.df_type:
            #butlist.append(create_edit_button())
            #self.buttons[index] = butlist[0]
            if self.df_type == 'recipe':
                if row['item'] == 'recipe':
                    butlist.append(create_search_button())
                else:
                    butlist.append(create_lookup_button())
            elif self.df_type == 'guide':
                butlist.append(create_duplicate_button())
            elif self.df_type == 'mentions':
                butlist.append(create_lookup_button())
                
            self.buttons[index] = butlist[0]
            items.append(widgets.HBox(butlist))

            
        # Create a Text widget for each cell in the row
        for col in self.df.columns:
            is_disabled = (col not in self.enabled_columns) or (self.df_type == 'mentions' and col == 'ingredient')
            # hide cell visibility
            hide = False
            # Simplifying value assignment and handling for 'myval'
            if str(row[col]) not in [str(np.nan), '']:
                 myval = row[col]
            else:
                myval = ''
                hide = True
            #myval = row[col] if str(row[col]) not in [str(np.nan), ''] else '-'
            myval = f"{myval:0.2f}" if isinstance(myval, float) else myval

            # Widget assignment based on 'item' and 'df_type'
            if col == 'item':
                if myval == 'recipe':
                    cell_widget = widgets.Label(value='recipe for:', layout=self.getlayout(col), style={'font_style': 'italic'})
                elif self.df_type == 'mentions':
                    cell_widget = widgets.Label(value=str(myval), layout=self.getlayout())
                else:
                    cell_widget = widgets.Label()
            else:
                if is_disabled or (col == 'ingredient' and self.df_type == 'recipe' and row['item'] == 'recipe'):
                    cell_widget = widgets.Label(value=str(myval), layout=self.getlayout(col))
                else:
                    if (col == 'ingredient') and (self.df_type == 'recipe'):
                        cell_widget = None
                        if (myval == ''): # use combobox for blank item
                            cell_widget = widgets.Combobox(
                                value = str(myval),
                                options=tuple(self.all_ingredients),
                                ensure_option=False,
                                disabled=is_disabled,
                                continuous_update=False,
                                layout = self.getlayout(col)
                            )
                        else:
                            cell_widget = widgets.Text(
                                value = str(myval),
                                #options=tuple(self.all_ingredients),
                                ensure_option=False,
                                disabled=is_disabled,
                                continuous_update=False,
                                layout = self.getlayout(col)
                            )
                        cell_widget.observe(lambda change, col=col, cell_widget=cell_widget: on_text_change(change, col, cell_widget), 'value')
                    else:
                        cell_widget = widgets.Text(
                            value=str(myval), 
                            layout=self.getlayout(col), 
                            disabled=is_disabled, 
                            continuous_update=False
                        )
                        cell_widget.observe(lambda change, col=col, cell_widget=cell_widget: on_text_change(change, col, cell_widget), 'value')


            if (hide and is_disabled):
                cell_widget.layout.visibility = 'hidden'
            items.append(cell_widget)
            
                
    def on_duplicate_click(self, button):
        row = self.df.loc[button.tag]
        newdate = pd.to_datetime('today').strftime('%Y-%m-%d')
        if newdate != row['date']:
            newrow = row.copy()
            newrow['date'] = newdate
            # add only recognized guide columns
            newrow = newrow[self.cc.guide_columns]
            newdf = pd.DataFrame([newrow])
            self.cc.uni_g = pd.concat([self.cc.uni_g, newdf], ignore_index=True)

            # clear cost of each recipe containing ingredient
            mdf = self.cc.find_ingredient(row['nickname'])
            for i,m in mdf.iterrows():
                self.cc.set_item_ingredient(m['item'], row['nickname'], 'cost', 0)
                self.cc.clear_cost(m['item'])

            self.setdf(row['nickname'])
            self.update_display()
        else:
            print("Can't duplicate! Dates must be different")
    
        
    def on_search_click(self, button):
        # Retrieve the row from the DataFrame using the button's 'tag' attribute
        row = self.df.loc[button.tag]
        
        # load mentions of the ingredient
        if self.df_type == 'recipe':
            self.search_name(row['ingredient'])
        elif self.df_type == 'mentions':
            self.search_name(row['item'])
        elif self.df_type == 'guide':
            self.search_name(row['nickname'])
        self.update_display()

    def on_lookup_click(self, button):
        # Retrieve the row from the DataFrame using the button's 'tag' attribute
        row = self.df.loc[button.tag]
            
        # Update the DataFrame and the grid
        if self.df_type == 'recipe':
            if  row['item'] != 'recipe':
                self.trigger(row['ingredient'])
                #self.lookup_name(row['ingredient'])
                
                #self.update_display()

        elif self.df_type == 'mentions':
            self.trigger(row['item'])
            #self.lookup_name(row['item'])
            #self.update_display()

        button.disabled = True

    def search_name(self, search):
        self.df = self.cc.find_ingredient(search).reset_index(drop=True)
        # calculate cost for each mention
        for i, row in self.df.iterrows():
            cost = self.cc.item_cost(row['item'], row['ingredient'])
            
        self.df = self.cc.find_ingredient(search).reset_index(drop=True)
        self.df = self.df.loc[self.df['item'] != 'recipe']
        mycolumns =  [x for x in self.df.columns if x not in self.hide_columns]
        self.df = self.df[mycolumns]
        self.findtype()
        if self.df_type == 'mentions':
            if self.df.empty:
                return
        else:
            print("my type: ", self.df_type)
        self.update_column_width()
        
                
    def lookup_name(self, lookup):
    # Update the DataFrame and the grid
        self.setdf(lookup)
        self.findtype()
        if self.df_type == 'recipe':
            self.cc.recipe_cost(self.df.iloc[0]['ingredient'])
            self.setdf(lookup)



    def get_widget(self):
        return(self.grid)
    
    def display(self):
        # Display the GridBox
        with self.output:
            self.output.clear_output(wait=True)
            display(self.grid)
        display(self.output)

class DisplayDataFrameWidget(DataFrameWidget):
    def on_lookup_click(self, button):
        # Retrieve the row from the DataFrame using the button's 'tag' attribute
        row = self.df.loc[button.tag]
        # if a trigger was set
        if (self.trigger != None):
            if (self.df_type == 'recipe'):
                 if  row['item'] != 'recipe':
                    self.trigger(row['ingredient'])

            elif self.df_type == 'mentions':
                self.trigger(row['item'])
            elif (self.df_type == 'guide'):
                self.trigger(row['nickname'])

        button.disabled = True


############################


class DataFrameExplorer:
    def __init__(self, cc=CostCalculator()):
        self.df = pd.DataFrame()
        self.mentiondf = pd.DataFrame()
        self.allvals = allvals
        self.defcolor = widgets.Text().style.text_color
        self.fontstyle = {'font_size': '12pt'}
        self.excel_filename = 'amc_menu_database.xlsx'
        self.enabled_columns=['ingredient', 'quantity', 'price', 'menu price', 'size', 'saved cost', 'date', 'supplier', 'description', 'allergen', 'conversion']
        self.hide_columns = ['note', 'conversion', 'saved cost', 'equ quant', 'menu price']
        self.cc = cc
        self.cost_select_method = {'recent':pick_recent_cost, 
                                'maximum':pick_max_cost, 
                                'minimum':pick_min_cost,
                                'all':lambda x: x}
        

        # top utility displays
        cost_chooser = widgets.Text(value='menucost.xlsx')
        cost_button = widgets.Button(description='write cost excel')
        cost_button.on_click(lambda x: self.cc.ordered_xlsx(str(cost_chooser.value), cost_multipliers=self.df_widget.cost_multipliers))
        cost_display = widgets.HBox([widgets.Label(value='cost export filename'), cost_chooser, cost_button])
                             
        database_chooser = widgets.Text(value=self.excel_filename)
        loadbutton = widgets.Button(description=f'reload database')
            #button.tag = index  # Store the row index in the button's 'tag' attribute
        loadbutton.on_click(lambda x: self.reload_database(database_chooser.value))
        writebutton = widgets.Button(description='write database')
        writebutton.on_click(lambda x: self.cc.write_cc(f"{database_chooser.value}"))
        database_display = widgets.HBox([widgets.Label(value='Database filename:'), database_chooser, loadbutton, writebutton])

        # add recipe
        addrecipe_text = widgets.Text(value='recipe name')
        addrecipe_button = widgets.Button(description='create recipe')
        addrecipe_button.on_click(lambda x: self.create_recipe(addrecipe_text))
        addrecipe_hbox = widgets.HBox([addrecipe_text, addrecipe_button])

        # main display

        # search combobox
        self.searchinput = widgets.Combobox(
            placeholder='ingredient/item',
            options=tuple(self.allvals),
            description='Search:',
            ensure_option=False,
            disabled=False,
            style=self.fontstyle
        )        
        self.searchinput.observe(self.update_search, names='value')

        # copy current display to clipboard
        copybutton = widgets.Button(description=f'copy sheet')
        copybutton.on_click(lambda x: self.df_widget.df.to_clipboard())

        hide_toggles = [widgets.Label(value='Show/Hide columns:', layout=widgets.Layout(width='40%'))]
        for col in self.hide_columns:
        # use saved cost check box
            hide_quant = widgets.Checkbox(
                value=False,
                description=col,
                disabled=False,
                indent=False
            )
            #hide_quant.observe(self.hide_col, names='value', col=hide_quant.description )
            hide_quant.observe(lambda change, col=col: self.hide_col(change, col), 'value')
            hide_toggles.append(hide_quant)
            
        hide_toggleVBox = widgets.HBox(hide_toggles)


                                      
        # use saved cost check box
        usesaved = widgets.Checkbox(
            value=False,
            description='Use saved cost',
            disabled=False,
            indent=False
        )
        usesaved.observe(self.usesaved, names='value')

        # set cost_picker
        cost_selection_widget = widgets.ToggleButtons(
            options=list(self.cost_select_method.keys()),
            description='Cost selection method:',
            disabled=False,
            button_style='', # 'success', 'info', 'warning', 'danger' or '',
        )
        cost_selection_widget.observe(self.cost_selector, names='value')
        

        # composition
        self.dfdisplay = widgets.Output(layout={ 'overflow': 'scroll', 'border': '1px solid black'})
        self.df_widget = DataFrameWidget(pd.DataFrame(), width='90px', enabled_columns=self.enabled_columns, 
                                         hide_columns=self.hide_columns, cc=self.cc, output=self.dfdisplay, trigger=self.trigger_update)

        # cost multipliers (cost 3.0x, cost 3.5x)
        cost_mult_input = widgets.FloatsInput(
            value=self.df_widget.cost_multipliers,
            format = '.2f'
        )
        cost_mult_input.observe(self.set_cost_multipliers, names='value')
        cost_mult_hbox = widgets.HBox([widgets.Label(value='Cost multipliers: '), cost_mult_input])

        
        topdisplay = widgets.VBox([widgets.HBox([self.searchinput, copybutton, usesaved]), self.dfdisplay], layout={'border': '2px solid green'})
        
        
        # mentions display
        self.mdfdisplay = widgets.Output(layout={'border': '1px solid black'})        
        self.bottom_label = widgets.Label(value='items containing...', style=self.fontstyle)
        self.mdf_widget = DisplayDataFrameWidget(pd.DataFrame(), width='90px', enabled_columns=[], 
                                         hide_columns=self.hide_columns, cc=self.cc, output=self.mdfdisplay, trigger=self.trigger_mentions)
        bottom_display = widgets.VBox([self.bottom_label, self.mdfdisplay], layout={'border': '2px solid blue'})
        
        
        # display composistion
        # combined display
        self.vbox = widgets.VBox([database_display, cost_display, addrecipe_hbox, hide_toggleVBox, cost_selection_widget, cost_mult_hbox, topdisplay, bottom_display])

        
    def trigger_mentions(self, iname):
        # reload current search in no iname
        if iname == None:
            iname = self.searchinput.value
        else:
            self.searchinput.value = iname
        #self.update_search({'new':iname, 'owner':self.searchinput})
    
    def trigger_update(self, iname):
        self.searchinput.value = iname
        #self.update_mentions(iname)
        
    def update_search(self, change):
        if change['new'] in self.allvals:
            change['owner'].style.text_color = self.defcolor
            iname = change['new']

            self.df_widget.lookup_name(iname)
            self.df_widget.update_display()
            self.update_mentions(iname)

        else:
            change['owner'].style.text_color = 'red'

    def cost_selector(self, change):
        method = change['new']
        self.cc.cost_picker = self.cost_select_method[method]
        # clear all costs
        self.cc.costdf['cost'] = 0
        self.df_widget.lookup_name(self.df_widget.last_lookup)
        self.df_widget.update_display()

        
    def set_cost_multipliers(self, change):
        self.df_widget.cost_multipliers = change['new']
        if (self.df_widget.df_type == 'recipe'):
            self.df_widget.lookup_name(self.df_widget.last_lookup)
            self.df_widget.update_display()
        
    def hide_col(self, change, col):
        ''' set a column to hide or not
        '''
        hide = change['new']
        if hide:
            self.hide_columns = set(self.hide_columns) - {col}
        else:
            self.hide_columns = set(self.hide_columns).union({col})
            
        self.df_widget.hide_columns = self.hide_columns
        self.df_widget.lookup_name(self.df_widget.last_lookup)
        self.df_widget.update_display()

    def usesaved(self, change):
        # set cc to use saved cost depending on user checkbox
        
        self.cc.use_saved = change['new']
        
        # recompute all?
        self.cc.costdf['cost'] = 0            
        self.df_widget.lookup_name(self.df_widget.last_lookup)
        self.df_widget.update_display()
        
    def update_mentions(self, iname):
        self.mdf_widget.search_name(iname)
        if self.mdf_widget.df.empty:
            return
        self.mdf_widget.update_display()
        self.bottom_label.value = f"items containing {iname}:"
    
    def reload_database(self, database):
        self.cc.read_from_xlsx(database)
        nicks = set(cc.uni_g['nickname'].dropna().unique())
        ingrs = set(cc.costdf['ingredient'].dropna().unique())
        self.allvals = nicks.union(ingrs)
        self.searchinput.options = tuple(self.allvals)
        self.df_widget.all_ingredients = self.allvals

    def create_recipe(self, textbox):
        ''' add new recipe to menu
        '''
        # check recipe dne
        rname = textbox.value.strip()
        if self.cc.findframe(rname).empty:
            # add to costdf
            #newdf = pd.DataFrame(data={'item':['recipe', rname], 'ingredient':[rname, 'water'], 'quantity':['1 ct', '1 cup']})
            newdf = pd.DataFrame(
                data={'item':['recipe'], 
                      'ingredient':[rname], 
                      'quantity':['1 ct']}
            )
            self.cc.costdf = pd.concat([self.cc.costdf, newdf], ignore_index=True)
            nicks = set(cc.uni_g['nickname'].dropna().unique())
            ingrs = set(cc.costdf['ingredient'].dropna().unique())
            self.allvals = nicks.union(ingrs)
            self.searchinput.options = tuple(self.allvals)
            self.df_widget.all_ingredients = self.allvals
        else:
            print(f'recipe/ingredient {rname} already exists')
    
    def display(self):
        display(self.vbox)

    
        
# Create an instance of DataFrameExplorer
explorer = DataFrameExplorer(cc=cc)
explorer.display()


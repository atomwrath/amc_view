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
my_allergens = ['gluten', 'dairy', 'egg', 'soy', 'fish', 'shellfish', 'tree-nut', 'peanut', 'poultry', 'sesame']

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
        # self.defcolor = widgets.Text().style.text_color
        self.width = width
        self.column_width = {}
        self.df_type = None
        self.enabled_columns = enabled_columns if enabled_columns else []
        self.hide_columns = hide_columns if hide_columns else []
        self.cc = cc
        nicks = set(cc.uni_g['nickname'].dropna().unique())
        ingrs = set(cc.costdf['ingredient'].dropna().unique())
        self.all_ingredients = nicks.union(ingrs)
        self.output = output
        self.backbutton = widgets.Button(description='Back')
        self.ingaccordian = widgets.Accordion()
        self.num_cols = 0
        self.trigger = trigger
        self.last_lookup = ''
        self.search_history = []
        self.cost_multipliers = []
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
        self.menulist = ['breakfast', 'lunch', 'dinner', 'deserts']
        
    def setdf(self, mylookup):
        self.last_lookup = mylookup
        mydf =  self.cc.findframe(mylookup).reset_index(drop=True).copy()
        self.df = mydf
        self.findtype()
        if (self.df_type == 'recipe'):
            colorder = ['item', 'ingredient', 'quantity', 'cost', 'equ quant']
            
            # add allergen column
            mydf['allergen'] = mydf['ingredient'].apply(lambda x: ', '.join(self.cc.findNset_allergens(x)))
            
            mydf = reorder_columns(mydf, colorder)
            mycolumns = [x for x in mydf.columns if x not in self.hide_columns]
            mydf = mydf[mycolumns]
            for cm in self.cost_multipliers:
                if cm > 0:
                    add_costx(mydf, cm)
            self.df = mydf
            self.update_column_width()
        else:
            mycolumns = mydf.columns
            if (self.df_type == 'guide'):
                #mycolumns = [x for x in mydf.columns if x not in ['myconversion', 'mycost']]
                mycolumns = ['description', 'brand', 'allergen']
            else:
                mycolumns =  [x for x in mydf.columns if x not in self.hide_columns]
            mydf = mydf[mycolumns]
            self.df = mydf
            self.update_column_width()
            
    def update_column_width(self):
        def carlen(myval):
            myval = f"{myval:0.2f}" if isinstance(myval, float) else myval
            return len(str(myval))
    
        try:
            maxlen = self.df.applymap(lambda x: 5 + 10 * carlen(x)).max().to_dict()
        except:
            maxlen = self.width
    
        cn_len = {c: 5 + 8 * len(str(c)) for c in self.df.columns}
    
        self.column_width = {c: max(maxlen[c], cn_len[c]) for c in maxlen}
        if self.df_type == 'recipe':
            self.column_width['item'] = 5+8*len('recipe for:')

    def update_display(self):
        """
        Update the display with widgets for each cell of the DataFrame.
        Display a button for the ingredient, labels for the other columns, and an Accordion for ingredients.
        Add a header label row for the column names on the same row as the back button.
        Ensure consistent height for all widgets in a row when Accordion is collapsed.
        
        Parameters:
        self: Object instance containing df, df_type, search_history, and other relevant attributes.
        """
        def addweight(row):
            row['weight'] = self.cc.do_conversion(row['ingredient'], str(row['quantity']), '1 g')
            return row
        
        def ingredients_by_weight(ing, quant):
            rdf = self.cc.flatten_recipe(ing, quant)
            rdf = rdf.apply(addweight, axis=1)
            return list(rdf.sort_values(by='weight', ascending=False)['ingredient'])
                    
        button_height = '33px'  # Adjust the height to match desired appearance
        min_button_width = 100  # Minimum width to ensure readability
        
        # Calculate maximum text length for each column
        max_lengths = {}
        for col in self.df.columns:
            max_lengths[col] = max(self.df[col][1:].astype(str).map(len).max(), len(col)) * 8  # Approximate character width
        
        # Create 'Back' button
        self.backbutton.layout = widgets.Layout(width=f'{max_lengths.get("ingredient", min_button_width)}px', height=button_height)
        if len(self.search_history) > 1:
            self.backbutton.on_click(self.on_back_click)
            self.backbutton.disabled = False
        else:
            self.backbutton.disabled = True
            
        # Create header labels for each column
        header_widgets = []
        header_widgets.append(widgets.Label(value="item", layout=widgets.Layout(width=f'{max_lengths.get("ingredient", min_button_width)}px', height=button_height)))

        for col in self.df.columns:
            if col in ['allergen']:
                header_widgets.append(widgets.Label(value=col.capitalize(), layout=widgets.Layout(width=f'{max_lengths.get(col, min_button_width)}px', height=button_height)))
        
        # Add a header for the ingredients column
        header_widgets.append(widgets.Label(value="Ingredients", layout=widgets.Layout(width=f'{min_button_width * 2}px', height=button_height)))
        
        # Create a HBox for the header row
        header_hbox = widgets.HBox(header_widgets)
        
        # Create a list to hold row widgets
        rows = []
        
        # Iterate through DataFrame rows and create widgets for each cell
        for index, row in self.df.iterrows():
            row_widgets = []
            
            if self.df_type in ['guide', None]:
                continue  # Skip processing for 'guide' and None types
            
            inglist = []
            if self.df_type == 'recipe':
                if index == 0:
                    if row['ingredient'] in self.menulist:
                        continue
                    
                    inglist = []
                    if 'ingredient list' in self.df.columns:
                        inglist = row['ingredient list']
                        if isinstance(inglist, str) and len(inglist) > 1:
                            inglist = row['ingredient list'].split(',')
                        else:
                            if row['ingredient'] in self.menulist:
                                pass
                            else:
                                inglist = ingredients_by_weight(row['ingredient'], row['quantity'])
                                self.cc.costdf.loc[self.cc.costdf['ingredient'] == row['ingredient'], 'ingredient list'] = ",".join(inglist)
                    else:
                        if row['ingredient'] in self.menulist:
                            pass
                        else:
                            inglist = ingredients_by_weight(row['ingredient'], row['quantity'])
                            self.cc.costdf.loc[self.cc.costdf['ingredient'] == row['ingredient'], 'ingredient list'] = ",".join(inglist)
                    if isinstance(inglist, list) and len(inglist) > 1:
                        ingredient_list = widgets.VBox([widgets.Label(value=ing) for ing in inglist])
                        self.ingaccordian.children = (ingredient_list,)
                        self.ingaccordian.set_title(0, f"Ingredients ({len(inglist)})")
                        self.ingaccordian.layout.width = f'{min_button_width * 2}px'
                        self.ingaccordian.layout.min_height = button_height  # Match button height when collapsed
                        self.ingaccordian.layout.max_height = '200px'  # Limit the height when expanded
                        self.ingaccordian.selected_index = None  # Start collapsed
                    else:
                        self.ingaccordian.children = (widgets.VBox(),)
                        
                    continue  # Skip the first row for 'recipe' type
                ingredient = row['ingredient']
            elif self.df_type == 'mentions':
                ingredient = row['item']
            
            # Create a button for the ingredient
            button_width = max(min_button_width, max_lengths.get('ingredient', min_button_width))
            button = widgets.Button(description=ingredient, layout=widgets.Layout(width=f'{button_width}px', height=button_height))
            button.on_click(self.make_on_click(ingredient))
            row_widgets.append(button)
            
            # Create labels for the other columns
            for col in self.df.columns:
                if col in ['ingredient', 'item', 'menu price']:
                    continue
                elif col in ['allergen']:
                    label_width = max(min_button_width, max_lengths.get(col, min_button_width))
                    label = widgets.Label(value=str(row[col]), layout=widgets.Layout(width=f'{label_width}px', height=button_height, margin='0px 5px 0px 0px'))
                    row_widgets.append(label)
            
            # accordion / label for ingredient list
            inglist = []
            accordion = None
            if self.cc.is_ingredient(row['ingredient']) or len(self.cc.get_children(row['ingredient'])) <= 1:
                accordion = widgets.Label(layout=widgets.Layout(width=f'{min_button_width * 2}px', height=button_height))
            else:
                # Create an Accordion for ingredients
                if 'ingredient list' in self.df.columns:
                    inglist = row['ingredient list']
                    if isinstance(inglist, str) and len(inglist) > 1:
                        inglist = row['ingredient list'].split(',')
                    else:
                        inglist = ingredients_by_weight(row['ingredient'], row['quantity'])
                        self.cc.costdf.loc[self.cc.costdf['ingredient'] == row['ingredient'], 'ingredient list'] = ",".join(inglist)
                else:
                    inglist = ingredients_by_weight(row['ingredient'], row['quantity'])
                    self.cc.costdf.loc[self.cc.costdf['ingredient'] == row['ingredient'], 'ingredient list'] = ",".join(inglist)
                
                if len(inglist) > 1:
                    ingredient_list = widgets.VBox([widgets.Label(value=ing) for ing in inglist])
                    accordion = widgets.Accordion(children=[ingredient_list])
                    accordion.set_title(0, f"Ingredients ({len(inglist)})")
                    accordion.layout.width = f'{min_button_width * 2}px'
                    accordion.layout.padding = '0px'
                    accordion.layout.margin = '0px'
                    accordion.layout.border = '0px'
                    accordion.layout.min_height = '20px'  # Match button height when collapsed
                    accordion.layout.max_height = '200px'  # Limit the height when expanded
                    accordion.selected_index = None  # Start collapsed
                
                    # Function to adjust height when Accordion is opened/closed
                    def on_accordion_change(change):
                        if change['new'] is None:  # Collapsed
                            accordion.layout.height = button_height
                        else:  # Expanded
                            accordion.layout.height = 'auto'
                
                    accordion.observe(on_accordion_change, names='selected_index')
                else:
                    accordion = widgets.Label(layout=widgets.Layout(width=f'{min_button_width * 2}px', height=button_height))
        
            row_widgets.append(accordion)
            
            # Create a HBox for the row and add to rows list
            row_hbox = widgets.HBox(row_widgets, layout=widgets.Layout(align_items='flex-start'))
            rows.append(row_hbox)
        
        # Create a VBox for all rows
        rows_vbox = widgets.VBox(rows)
        
        # Combine the back button and header row
        button_and_header_vbox = widgets.VBox([header_hbox, rows_vbox])
        
        # Combine buttons and DataFrame rows display
        display_layout = widgets.HBox([button_and_header_vbox], layout=widgets.Layout(align_items='flex-start'))
        
        # Clear previous output and display the new layout
        with self.output:
            self.output.clear_output(wait=True)
            display(display_layout)
        
        # Trigger the specified function if provided
        if self.trigger:
            if self.df_type == 'recipe':
                self.trigger(self.df.iloc[0]['ingredient'])
            elif self.df_type == 'guide':
                self.trigger(self.df.loc[0]['nickname'])
            
            
    def update_display2(self):
        """
        Update the display with widgets for each cell of the DataFrame.
        Display a button for the ingredient, labels for the other columns, and a combo box for each row.
        Add a header label row for the column names on the same row as the back button.
        
        Parameters:
        self: Object instance containing df, df_type, search_history, and other relevant attributes.
        """
        button_height = '26px'  # Adjust the height to match desired appearance
        min_button_width = 100  # Minimum width to ensure readability
        combo_box_options = ['Option 1', 'Option 2', 'Option 3']  # Example options for combo boxes
        
        # Calculate maximum text length for each column
        max_lengths = {}
        for col in self.df.columns:
            max_lengths[col] = max(self.df[col][1:].astype(str).map(len).max(), len(col)) * 8  # Approximate character width
        
        # Create 'Back' button
        self.backbutton.layout = widgets.Layout(width=f'{max_lengths.get("ingredient", min_button_width)}px', height=button_height)
        if len(self.search_history) > 1:
            self.backbutton.on_click(self.on_back_click)
            self.backbutton.disabled = False
        else:
            self.backbutton.disabled = True
             
        # Create header labels for each column
        header_widgets = []
        #header_widgets.append(backbutton)
        header_widgets.append(widgets.Label(value="ingredient", layout=widgets.Layout(width=f'{max_lengths.get(col, min_button_width)}px', height=button_height)))
    
        for col in self.df.columns:
            if col in ['allergen']:
                header_widgets.append(widgets.Label(value=col.capitalize(), layout=widgets.Layout(width=f'{max_lengths.get(col, min_button_width)}px', height=button_height)))
        
        # Add a header for the combo box column
        header_widgets.append(widgets.Label(value="Ingredients", layout=widgets.Layout(width=f'{min_button_width}px', height=button_height)))
        
        # Create a HBox for the header row
        header_hbox = widgets.HBox(header_widgets)
        
        # Create a list to hold row widgets
        rows = []
        
        # Iterate through DataFrame rows and create widgets for each cell
        for index, row in self.df.iterrows():
            row_widgets = []
            
            if self.df_type in ['guide', None]:
                continue  # Skip processing for 'guide' and None types
            
            if self.df_type == 'recipe':
                if index == 0:
                    self.ingcombobox.options = [x for x in self.cc.get_all_children(row['ingredient'], set()) if self.cc.is_ingredient(x)]
                    self.ingcombobox.placeholder='ingredients'
                    self.ingcombobox.ensure_option=False
                    continue  # Skip the first row for 'recipe' type
                ingredient = row['ingredient']
            elif self.df_type == 'mentions':
                ingredient = row['item']
            
            # Create a button for the ingredient
            button_width = max(min_button_width, max_lengths.get('ingredient', min_button_width))
            button = widgets.Button(description=ingredient, layout=widgets.Layout(width=f'{button_width}px', height=button_height))
            button.on_click(self.make_on_click(ingredient))
            row_widgets.append(button)
            
            # Create labels for the other columns
            for col in self.df.columns:
                if col in ['ingredient', 'item', 'menu price']:
                    continue
                label_width = max(min_button_width, max_lengths.get(col, min_button_width))
                label = widgets.Label(value=str(row[col]), layout=widgets.Layout(width=f'{label_width}px', height=button_height, margin='0px 5px 0px 0px'))
                row_widgets.append(label)
            
            # Create a combo box for the row
            combo_box_options = [x for x in self.cc.get_all_children(ingredient, set()) if self.cc.is_ingredient(x)]
            if len(combo_box_options) > 1:
                combo_box = widgets.Combobox(options=combo_box_options, layout=widgets.Layout(width=f'{min_button_width}px', height=button_height))
                combo_box.placeholder='ingredients'
                combo_box.ensure_option=False
            else:
                combo_box = widgets.Label(layout=widgets.Layout(width=f'{min_button_width}px', height=button_height))
            # Function to update combo box text color
            def on_combo_change(change):
                if change['new'] not in combo_box_options:
                    combo_box.layout.color = 'red'
                else:
                    combo_box.layout.color = 'black'
            
            combo_box.observe(on_combo_change, names='value')
            row_widgets.append(combo_box)
            
            # Create a HBox for the row and add to rows list
            row_hbox = widgets.HBox(row_widgets)
            rows.append(row_hbox)
        
        # Create a VBox for all rows
        rows_vbox = widgets.VBox(rows)
        
        # Combine the back button and header row
        button_and_header_vbox = widgets.VBox([header_hbox, rows_vbox])
        
        # Combine buttons and DataFrame rows display
        display_layout = widgets.HBox([button_and_header_vbox], layout=widgets.Layout(align_items='stretch'))
        
        # Clear previous output and display the new layout
        with self.output:
            self.output.clear_output(wait=True)
            display(display_layout)
        
        # Trigger the specified function if provided
        if self.trigger:
            if self.df_type == 'recipe':
                self.trigger(self.df.iloc[0]['ingredient'])
            elif self.df_type == 'guide':
                self.trigger(self.df.loc[0]['nickname'])


    def update_displayold(self):
        # Create buttons for each row
        buttons = []
        button_height = '26px'  # Adjust the height to match 
        backbutton = widgets.Button(description='Back', layout=widgets.Layout(width='auto', height=button_height))
        if len(self.search_history) > 1:
            backbutton.on_click(self.on_back_click)
        else:
            backbutton.disabled = True
        buttons.append(backbutton)
        for index, row in self.df.iterrows():
            mying = ''
            if self.df_type == 'guide' or self.df_type == None:
                pass
            else:
                if self.df_type == 'recipe':
                    if index == 0:
                        continue
                    mying = row['ingredient']
                elif self.df_type == 'mentions':
                    mying = row['item']
                    
                button = widgets.Button(description=mying, layout=widgets.Layout(width='auto', height=button_height))
                button.on_click(self.make_on_click(mying))
                buttons.append(button)
            
        
        button_vbox = widgets.VBox(buttons, layout=widgets.Layout(width='120px'))  # Adjust width to match DataFrame
        
        
        # Display the DataFrame
        df_output = widgets.Output(layout=widgets.Layout(overflow='auto'))
        with df_output:
            if self.df_type == 'mentions':
                display(self.df.style.hide(axis='index'))
            else:
                display(self.df[1:][[x for x in self.df.columns if x != 'item']].style.hide(axis='index'))
        
        # Combine buttons and DataFrame display
        display_layout = widgets.HBox([button_vbox, df_output], layout=widgets.Layout(align_items='stretch'))
        
        with self.output:
            self.output.clear_output(wait=True)
            display(display_layout)

        if self.trigger:
            if self.df_type == 'recipe':
                self.trigger(self.df.iloc[0]['ingredient'])
            elif self.df_type == 'guide':
                self.trigger(self.df.loc[0]['nickname'])

    def make_on_click(self, ingredient):
        def on_click(button):
            #self.search_history.append(ingredient)
            self.lookup_name(ingredient)
            self.update_display()
        return on_click
    
    def on_back_click(self, button):
        if len(self.search_history) > 1:
            self.search_history.pop()
            previous = self.search_history.pop()  # Get the last search term
            self.lookup_name(previous)
            self.update_display()  # Update the display after going back

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

    def search_name(self, search):
        self.df = self.cc.find_ingredient(search).reset_index(drop=True)
            
        self.df = self.cc.find_ingredient(search).reset_index(drop=True)
        self.df = self.df.loc[self.df['item'] != 'recipe']
        mycolumns =  [x for x in self.df.columns if x not in self.hide_columns]
        self.df = self.df[mycolumns]
        self.findtype()
        if self.df_type == 'mentions':
            if self.df.empty:
                return
        else:
            pass
            # print("my type: ", self.df_type)
        self.update_column_width()
        
    def lookup_name(self, lookup):
    # Update the DataFrame and the grid
        self.setdf(lookup)
        self.findtype()
        if self.search_history:
            if lookup != self.search_history[-1]:
                self.search_history.append(lookup)
        else:
            self.search_history.append(lookup)
        if self.df_type == 'recipe':
            #self.cc.recipe_cost(self.df.iloc[0]['ingredient'])
            self.setdf(lookup)
    
    def display(self):
        with self.output:
            self.output.clear_output(wait=True)
            display(self.grid)
        display(self.output)


class DisplayDataFrameWidget(DataFrameWidget):
    def on_lookup_click(self, button):
        row = self.df.loc[button.tag]
        if self.trigger:
            if self.df_type == 'recipe' and row['item'] != 'recipe':
                self.trigger(row['ingredient'])
            elif self.df_type == 'mentions':
                self.trigger(row['item'])
            elif self.df_type == 'guide':
                self.trigger(row['nickname'])
        button.disabled = True

class DataFrameExplorer:
    def __init__(self, cc=CostCalculator()):
        self.df = pd.DataFrame()
        self.mentiondf = pd.DataFrame()
        self.allvals = allvals
        #self.defcolor = widgets.Text().style.text_color
        self.fontstyle = {'font_size': '12pt'}
        self.excel_filename = 'amc_menu_database.xlsx'
        self.enabled_columns=['ingredient', 'quantity', 'price', 'size', 'saved cost', 'menu cost', 'date', 'supplier', 'description']
        self.hide_columns = ['cost', 'note', 'conversion', 'saved cost', 'equ quant']
        self.cc = cc
        self.cost_select_method = {'recent':pick_recent_cost, 
                                'maximum':pick_max_cost, 
                                'minimum':pick_min_cost,
                                'all':lambda x: x}
        
        # UI section
        self.searchinput = widgets.Combobox(
            placeholder='ingredient/item',
            options=tuple(self.allvals),
            description='Search:',
            ensure_option=False,
            disabled=False,
            style=self.fontstyle
        )        
        self.searchinput.observe(self.update_search, names='value')
        
        
        self.dfdisplay = widgets.Output(layout={ 'overflow': 'scroll', 'border': '1px solid black'})
        self.df_widget = DataFrameWidget(pd.DataFrame(), width='90px', enabled_columns=self.enabled_columns, 
                                         hide_columns=self.hide_columns, cc=self.cc, output=self.dfdisplay, trigger=self.trigger_update)
        # Create 'Back' button
        self.backbutton = self.df_widget.backbutton
        self.ingaccordian = self.df_widget.ingaccordian
        topdisplay = widgets.VBox([widgets.HBox([self.backbutton, self.searchinput, self.ingaccordian]), self.dfdisplay], layout={'border': '2px solid green'})
        
        self.mdfdisplay = widgets.Output(layout={'border': '1px solid black'})        
        self.bottom_label = widgets.Label(value='items containing...', style=self.fontstyle)
        self.mdf_widget = DisplayDataFrameWidget(pd.DataFrame(), width='90px', enabled_columns=[], 
                                         hide_columns=self.hide_columns, cc=self.cc, output=self.mdfdisplay, trigger=self.trigger_mentions)
        bottom_display = widgets.VBox([self.bottom_label, self.mdfdisplay], layout={'border': '2px solid blue'})
        
                
        menulist = ['breakfast', 'lunch', 'dinner', 'deserts']
        menubuttons = []
        for menu in menulist:
            button = widgets.Button(description=menu, layout=widgets.Layout(width='auto'))
            button.on_click(self.df_widget.make_on_click(menu))
            menubuttons.append(button)
            
        menubutton_hbox = widgets.HBox(menubuttons, layout=widgets.Layout(width='auto'))  # Adjust width to match DataFrame
        
        # Function to handle checkbox changes
        def toggle_on_change(change):
            if change['type'] == 'change' and change['name'] == 'value':
                print(f"{change['owner'].description} is now {'checked' if change['new'] else 'unchecked'}")

        # Create checkboxes for each allergen
        checkboxes = [widgets.Checkbox(value=False, description=allergen) for allergen in my_allergens]

        # Attach the on_change event handler to each checkbox
        for checkbox in checkboxes:
            checkbox.observe(toggle_on_change)

        
        # Arrange checkboxes into rows of HBoxes with 4 or fewer entries each
        rows = [widgets.HBox(checkboxes[i:i+4]) for i in range(0, len(checkboxes), 4)]

        # Display the rows of checkboxes
        checkbox_box = widgets.VBox(rows)
        
        self.vbox = widgets.VBox([menubutton_hbox, topdisplay, bottom_display])

    def trigger_mentions(self, iname):
        if iname == None:
            iname = self.searchinput.value
        else:
            self.searchinput.value = iname
    
    def trigger_update(self, iname):
        self.searchinput.value = iname
        
    def update_search(self, change):
        if change['new'] in self.allvals:
            # change['owner'].style.text_color = self.defcolor
            iname = change['new']
            self.df_widget.lookup_name(iname)
            self.df_widget.update_display()
            self.update_mentions(iname)
        else:
            change['owner'].style.text_color = 'red'

    def cost_selector(self, change):
        method = change['new']
        self.cc.cost_picker = self.cost_select_method[method]
        self.cc.costdf['cost'] = 0
        self.df_widget.lookup_name(self.df_widget.last_lookup)
        self.df_widget.update_display()

    def set_cost_multipliers(self, change):
        self.df_widget.cost_multipliers = change['new']
        if self.df_widget.df_type == 'recipe':
            self.df_widget.lookup_name(self.df_widget.last_lookup)
            self.df_widget.update_display()
        
    def hide_col(self, change, col):
        hide = change['new']
        if hide:
            self.hide_columns = set(self.hide_columns) - {col}
        else:
            self.hide_columns = set(self.hide_columns).union({col})
            
        self.df_widget.hide_columns = self.hide_columns
        self.df_widget.lookup_name(self.df_widget.last_lookup)
        self.df_widget.update_display()

    def usesaved(self, change):
        self.cc.use_saved = change['new']
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
        nicks = set(self.cc.uni_g['nickname'].dropna().unique())
        ingrs = set(self.cc.costdf['ingredient'].dropna().unique())
        self.allvals = nicks.union(ingrs)
        self.searchinput.options = tuple(self.allvals)
        self.df_widget.all_ingredients = self.allvals

    def create_recipe(self, textbox):
        rname = textbox.value.strip()
        if self.cc.findframe(rname).empty:
            newdf = pd.DataFrame(data={'item':['recipe'], 'ingredient':[rname], 'quantity':['1 ct']})
            self.cc.costdf = pd.concat([self.cc.costdf, newdf], ignore_index=True)
            nicks = set(self.cc.uni_g['nickname'].dropna().unique())
            ingrs = set(self.cc.costdf['ingredient'].dropna().unique())
            self.allvals = nicks.union(ingrs)
            self.searchinput.options = tuple(self.allvals)
            self.df_widget.all_ingredients = self.allvals
        else:
            print(f'recipe/ingredient {rname} already exists')
    
    def display(self):
        display(self.vbox)

explorer = DataFrameExplorer(cc=cc)
explorer.display()

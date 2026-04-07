import sys
import os
import csv
import pandas as pd
from sqlalchemy.orm import sessionmaker

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal, engine
from app.models.defect_scheme import DefectScheme, DefectStep, DefectMaterial

def import_csv(file_path):
    print(f"Importing from {file_path}...")
    
    # Read CSV
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, encoding='gbk')
    
    # Fill NaN with empty strings or 0
    df = df.fillna('')
    
    session = SessionLocal()
    
    try:
        schemes_cache = {} # key: (comp_pn, defect_catalog) -> scheme_obj
        
        row_count = 0
        for index, row in df.iterrows():
            comp_pn = str(row['comp_p/n']).strip()
            if not comp_pn:
                continue
                
            try:
                defect_catalog = int(row['defect_catalog'])
            except:
                print(f"Skipping row {index}: Invalid defect_catalog")
                continue
                
            scheme_key = (comp_pn, defect_catalog)
            
            # 1. Handle Scheme
            if scheme_key not in schemes_cache:
                # Check DB
                existing = session.query(DefectScheme).filter_by(comp_pn=comp_pn, defect_catalog=defect_catalog).first()
                if existing:
                    scheme = existing
                else:
                    # Parse numerical fields
                    qty = 0
                    if row['Qty'] and str(row['Qty']).strip():
                        try:
                            qty = int(float(str(row['Qty'])))
                        except:
                            pass
                            
                    labor = 0.0
                    if row['LABOR'] and str(row['LABOR']).strip():
                        try:
                            labor = float(str(row['LABOR']))
                        except:
                            pass
                            
                    manhour = 0.0
                    if row['MANHOUR'] and str(row['MANHOUR']).strip():
                        try:
                            manhour = float(str(row['MANHOUR']))
                        except:
                            pass

                    scheme = DefectScheme(
                        comp_pn=comp_pn,
                        defect_catalog=defect_catalog,
                        jc_desc_cn=str(row['JC_DESC']).strip(),
                        jc_desc_en=str(row['JC_DESC_EN']).strip(),
                        key_words_1=str(row['key_words_1']).strip(),
                        key_words_2=str(row['key_words_2']).strip(),
                        trade=str(row['TRADE']).strip(),
                        zone=str(row['ZONE']).strip(),
                        loc=str(row['Loc']).strip(),
                        qty=qty,
                        jc_type=str(row['JC_TYPE']).strip(),
                        labor=labor,
                        manhour=manhour,
                        candidate_history_wo=str(row.get('Candidate_history_wo', '')).strip(),
                        refer_manual=str(row.get('Refer_Manual', '')).strip(),
                    )
                    session.add(scheme)
                    session.flush() # Get ID
                schemes_cache[scheme_key] = scheme
            else:
                scheme = schemes_cache[scheme_key]
            
            # 2. Handle Step
            try:
                step_num = int(row['steps_item'])
            except:
                step_num = 1 
            
            # Check if step exists (to avoid duplicates if running multiple times or bad data)
            # Actually, since we are iterating rows, and assuming one row per step, we just add it.
            # But if we run this script twice, we might duplicate steps if we don't check.
            # For simplicity, let's assume clean import or check existance.
            
            existing_step = session.query(DefectStep).filter_by(scheme_id=scheme.id, step_number=step_num).first()
            if existing_step:
                step = existing_step
                # Update info if needed?
            else:
                # Manhour per step?
                # The CSV structure is a bit flat. Let's assume MANHOUR in the row applies to the step 
                # if the scheme has multiple steps with different manhours.
                # But typically MANHOUR is for the whole job card.
                # However, for DefectStep, we can store it if provided.
                step_manhour = 0.0
                if row['MANHOUR'] and str(row['MANHOUR']).strip():
                    try:
                        step_manhour = float(str(row['MANHOUR']))
                    except:
                        pass

                step = DefectStep(
                    scheme_id=scheme.id,
                    step_number=step_num,
                    step_desc=str(row['STEP_DESC']).strip(),
                    step_desc_en=str(row['STEP_DESC_EN']).strip(),
                    manhour=step_manhour
                )
                session.add(step)
                session.flush()
            
            # 3. Handle Materials
            # "PN_REQUESTED,Amount,Unit,Remark" column
            # e.g. "861404-173E,1,EA;861404-108H,1,EA"
            col_name = "PN_REQUESTED,Amount,Unit,Remark"
            if col_name in row and row[col_name]:
                materials_str = str(row[col_name])
                if materials_str.lower() != 'nan' and materials_str.strip():
                    items = materials_str.split(';')
                    for item in items:
                        item = item.strip()
                        if not item: continue
                        
                        parts = item.split(',')
                        if len(parts) >= 1:
                            pn = parts[0].strip()
                            if not pn: continue
                            
                            amount = 1.0
                            unit = 'EA'
                            remark = ''
                            
                            if len(parts) >= 2:
                                try:
                                    amount = float(parts[1].strip())
                                except:
                                    pass
                            if len(parts) >= 3:
                                unit = parts[2].strip()
                            if len(parts) >= 4:
                                remark = parts[3].strip()
                            
                            # Check duplication
                            existing_mat = session.query(DefectMaterial).filter_by(
                                step_id=step.id, part_number=pn
                            ).first()
                            
                            if not existing_mat:
                                mat = DefectMaterial(
                                    step_id=step.id,
                                    part_number=pn,
                                    amount=amount,
                                    unit=unit,
                                    remark=remark
                                )
                                session.add(mat)
            
            row_count += 1
            if row_count % 100 == 0:
                print(f"Processed {row_count} rows...")
                        
        session.commit()
        print(f"Import completed successfully. Processed {row_count} rows.")
        
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_defect_schemes.py <csv_path>")
        sys.exit(1)
    
    import_csv(sys.argv[1])

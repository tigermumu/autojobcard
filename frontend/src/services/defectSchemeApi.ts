import axios from 'axios'

const API_BASE_URL = '/api/v1'

export interface DefectMaterial {
  id?: number
  step_id?: number
  material_seq?: number
  part_number: string
  amount?: number
  unit?: string
  remark?: string
}

export interface DefectStep {
  id?: number
  scheme_id?: number
  step_number: number
  step_desc_cn?: string
  step_desc_en?: string
  manhour?: number
  trade?: string
  manpower?: string
  refer_manual?: string
  materials: DefectMaterial[]
}

export interface DefectScheme {
  id?: number
  comp_pn: string
  defect_catalog?: number
  jc_desc_cn?: string
  jc_desc_en?: string
  type?: string
  cust?: string
  comp_name?: string
  key_words_1?: string
  key_words_2?: string
  trade?: string
  zone?: string
  loc?: string
  qty?: number
  jc_type?: string
  labor?: number
  manhour?: number
  candidate_history_wo?: string
  refer_manual?: string
  created_at?: string
  updated_at?: string
  steps: DefectStep[]
}

export const defectSchemeApi = {
  list: async (skip = 0, limit = 100, comp_pn?: string, keyword?: string): Promise<DefectScheme[]> => {
    const params: any = { skip, limit }
    if (comp_pn) params.comp_pn = comp_pn
    if (keyword) params.keyword = keyword
    
    const response = await axios.get(`${API_BASE_URL}/defect-schemes/`, { params })
    return response.data
  },

  create: async (scheme: DefectScheme): Promise<DefectScheme> => {
    const response = await axios.post(`${API_BASE_URL}/defect-schemes/`, scheme)
    return response.data
  },

  update: async (id: number, scheme: DefectScheme): Promise<DefectScheme> => {
    const response = await axios.put(`${API_BASE_URL}/defect-schemes/${id}`, scheme)
    return response.data
  },

  delete: async (id: number): Promise<void> => {
    await axios.delete(`${API_BASE_URL}/defect-schemes/${id}`)
  }
}

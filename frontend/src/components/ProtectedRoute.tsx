import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { Result, Spin } from 'antd'
import { useAuth } from '../contexts/AuthContext'

interface ProtectedRouteProps {
  children: React.ReactElement
  permissions?: string[]
  requireAny?: boolean
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, permissions = [], requireAny = false }) => {
  const location = useLocation()
  const { loading, isAuthenticated, hasPermission, hasAnyPermission } = useAuth()

  if (loading) {
    return <Spin size="large" style={{ display: 'block', margin: '120px auto' }} />
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  if (permissions.length > 0) {
    const allowed = requireAny
      ? hasAnyPermission(permissions)
      : permissions.every((item) => hasPermission(item))

    if (!allowed) {
      return <Result status="403" title="403" subTitle="当前账号没有访问该功能的权限" />
    }
  }

  return children
}

export default ProtectedRoute

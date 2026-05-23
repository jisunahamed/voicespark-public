import { Navigate, Outlet } from 'react-router-dom';
import { CircularProgress, Box } from '@mui/material';
import { useAuth } from './auth_context';
 
export default function PrivateRoute() {
  const { isAuthenticated, loading } = useAuth();
 
  if (loading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="100vh"
      >
        <CircularProgress />
      </Box>
    );
  }
 
  return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace />;
}
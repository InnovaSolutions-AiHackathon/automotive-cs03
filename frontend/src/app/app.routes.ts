import { Routes } from '@angular/router';
import { DashboardHomeComponent } from './components/dashboard-home/dashboard-home-component';
import { VehicleDashboardComponent } from './components/vehicle-dashboard/vehicle-dashboard.component';
import { CopilotPanelComponent } from './components/copilot-panel/copilot-panel.component';
import { VehiclesinfoComponent } from './components/vehicles-info/vehicles-info.component';
import { LoginComponent } from './components/login/login.component';
import { SignupComponent } from './components/signup/signup.component';
import { Warranty } from './components/warranty/warranty';
import { Scheduling} from './components/scheduling/scheduling';
import { Reports } from './components/reports/reports';

import { authGuard } from './guards/auth.guard';

export const routes: Routes = [

  // AUTH ROUTES (no sidebar)
  { path: '', component: LoginComponent },
  { path: 'signup', component: SignupComponent },

  // APP LAYOUT (with sidebar)
  {
    path: '',
    component: DashboardHomeComponent,
    canActivate: [authGuard],
    children: [
      { path: 'home', component: VehicleDashboardComponent },
      { path: 'dashboard', component: VehicleDashboardComponent },
      { path: 'copilot', component: CopilotPanelComponent },
      { path: 'vehicles-info', component: VehiclesinfoComponent },
      { path: 'warranty', component: Warranty },
      { path: 'scheduling', component: Scheduling },
      { path: 'reports', component: Reports },
    ]
  }
];
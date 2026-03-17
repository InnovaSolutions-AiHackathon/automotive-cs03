import { Routes } from '@angular/router';
import { VehicleDashboardComponent } from './components/vehicle-dashboard/vehicle-dashboard.component';
import { CopilotPanelComponent } from './components/copilot-panel/copilot-panel.component';
import { VehiclesinfoComponent } from './components/vehicles-info/vehicles-info.component';

export const routes: Routes = [
  { path: '', component: VehicleDashboardComponent },
  { path: 'copilot', component: CopilotPanelComponent },
  { path: 'vehicles-info', component: VehiclesinfoComponent }
];
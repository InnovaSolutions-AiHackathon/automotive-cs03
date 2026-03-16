import { Routes } from '@angular/router';
import { VehicleDashboardComponent } from './components/vehicle-dashboard/vehicle-dashboard.component';
import { CopilotPanelComponent } from './components/copilot-panel/copilot-panel.component';
import { WarrantyBadgeComponent } from './components/warranty-badge/warranty-badge.component';

export const routes: Routes = [
  { path: '', component: VehicleDashboardComponent },
  { path: 'copilot', component: CopilotPanelComponent },
  { path: 'warranty', component: WarrantyBadgeComponent }
];
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { CopilotPanelComponent } from './components/copilot-panel/copilot-panel.component';
import { VehicleDashboardComponent } from './components/vehicle-dashboard/vehicle-dashboard.component';
import { WarrantyBadgeComponent } from './components/warranty-badge/warranty-badge.component';

const routes: Routes = [
  { path: '', component: VehicleDashboardComponent },
  { path: 'copilot', component: CopilotPanelComponent },
  { path: 'warranty', component: WarrantyBadgeComponent }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule {}
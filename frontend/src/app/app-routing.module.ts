import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { CopilotPanelComponent } from './components/copilot-panel/copilot-panel.component';
import { VehicleDashboardComponent } from './components/vehicle-dashboard/vehicle-dashboard.component';
import { VehiclesinfoComponent } from './components/vehicles-info/vehicles-info.component';

const routes: Routes = [
  { path: '', component: VehicleDashboardComponent },
  { path: 'copilot', component: CopilotPanelComponent },
  { path: 'vehicles-info', component: VehiclesinfoComponent }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule {}
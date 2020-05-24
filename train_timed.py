import torch
from utils import show_image
from pathlib import Path
import time

class train_model:
    def __init__(self, device, tb=None):
        self.path = Path('./experiments/')
        self.device = device
        self.globaliter = 0
        self.tb = tb

    def train(self, model, criterion, metric, train_loader, optimizer, epoch):
        dtd_time=0
        ozg_time=0
        mp_time=0
        lc_time=0
        lbg_time=0
        os_time=0
        tb_time=0
        iou_time=0
        pr_time=0
        sd_time=0
        tot_time=0
        model.train()
        for batch_idx, data in enumerate(train_loader):
            t0 = time.time()
            data['i1'] = data['i1'].to(self.device)
            data['i2'] = data['i2'].to(self.device)
            data['o1'] = data['o1'].to(self.device)
            t1 = time.time()
            dtd_time+=t1-t0
            # print("Data to device time: ", t1-t0)
            optimizer.zero_grad()  # making gradients 0, so that they are not accumulated over multiple batches
            t2 = time.time()
            ozg_time+=t2-t1
            # print("Optimizer zero grad time: ", t2-t1)
            output = model(data['i1'], data['i2'])
            t3 = time.time()
            mp_time+=t3-t2
            # print("Model prediction time: ", t3-t2)
            loss = criterion(output, data['o1'])
            t4 = time.time()
            lc_time+=t4-t3
            # print("Loss calculation time: ", t4-t3)
            # loss = loss.view(loss.shape[0], -1).sum(1).mean()
            loss.backward()  # calculating gradients
            t5 = time.time()
            lbg_time+=t5-t4
            # print("Loss backward gradient calculation time: ", t5-t4)
            optimizer.step()  # updating weights
            t6 = time.time()
            os_time+=t6-t5
            # print("Optimizer step time: ", t6-t5)
            # if self.tb:
            #     self.globaliter += 1
            #     self.tb.save_value('Train Loss', 'train_loss', self.globaliter, loss.item())
            t7 = time.time()
            tb_time+=t7-t6
            # print("Tensorboard: ", t7-t6)

            if batch_idx % 50 == 0:
                metric_value = 0
                if metric:
                    metric_value = metric(output, data['o1']).cpu().detach().numpy() / output.shape[0]
                t8 = time.time()
                iou_time+=t8-t7
                # print("IOU calc time: ", t8-t7)
                print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}\tMetric: {:.6f}'.format(
                    epoch, batch_idx * len(data['i1']), len(train_loader.dataset), 100. * batch_idx / len(train_loader),
                    loss.item(), metric_value))
                print('Batch ID: ', batch_idx)
                t9 = time.time()
                pr_time+=t9-t8
                # print("Printing time: ", t9-t8)
                # len(dataloader.dataset) --> total number of input images
                # len(dataloader) --> total no of batches, each to specified size like 16

            if batch_idx % 500 == 0:
                show_image(data['o1'][::4].cpu(), n_row=8, title='Target (Training)')
                show_image(output[::4].cpu(), n_row=8, title='Predicted (Training)')
                # print(output)
                # print(data['o1'])
                t10 = time.time()
                sd_time+=t10-t9
                # print("Samples Display time: ", t10-t9)

            if batch_idx % 1000 == 0:
                torch.save(model.state_dict(), self.path / f"{batch_idx}.pth")

            t11 = time.time()
            tot_time+=t11-t0
            if batch_idx == 549:
                print("Around 1/4th of an epoch: ")
                print("Total time: {}s".format(tot_time))
                print("Data to device time: {}s, {} % of total ".format(dtd_time, dtd_time*100/tot_time))
                print("Optimizer zero gard time: {}s, {} % of total ".format(ozg_time, ozg_time*100/tot_time))
                print("Model Prediction time: {}s, {} % of total ".format(mp_time, mp_time * 100 / tot_time))
                print("Loss calculation time: {}s, {} % of total ".format(lc_time, lc_time * 100 / tot_time))
                print("Gradient calculation time: {}s, {} % of total ".format(lbg_time, lbg_time * 100 / tot_time))
                print("Weights updating time: {}s, {} % of total ".format(os_time, os_time * 100 / tot_time))
                print("Tensorboard time: {}s, {} % of total ".format(tb_time, tb_time * 100 / tot_time))
                print("IOU calc time: {}s, {} % of total ".format(iou_time, iou_time * 100 / tot_time))
                print("Printing time: {}s, {} % of total ".format(pr_time, pr_time * 100 / tot_time))
                print("Sample Display time: {}s, {} % of total ".format(sd_time, sd_time * 100 / tot_time))
                break

    def validate(self, model, criterion, metric, valid_loader):
        # setting model evaluate mode, takes care of batch norm, dropout etc. not required while validation
        model.eval()
        valid_loss = 0
        correct = 0
        metric_value = 0
        with torch.no_grad():
            for batch_idx, data in enumerate(valid_loader):
                data['i1'] = data['i1'].to(self.device, dtype=torch.float)
                data['i2'] = data['i2'].to(self.device, dtype=torch.float)
                data['o1'] = data['o1'].to(self.device, dtype=torch.float)
                output = model(data['i1'], data['i2'])
                loss = criterion(output, data['o1'])
                valid_loss += loss.item()  # loss.view(loss.shape[0], -1).sum(1).mean().item()
                if metric:
                    metric_value += metric(output, data['o1']).cpu().detach().numpy() / output.shape[0]
        metric_value /= len(valid_loader)
        valid_loss /= len(valid_loader)
        print("Some target vs predicted samples:")
        show_image(data['o1'][::4].cpu(), n_row=8, title='Target (validation)')
        show_image(output[::4].cpu(), n_row=8, title='Predicted (validation)')
        print("Average Validation loss: {}\t Average IOU: {}".format(valid_loss, metric_value))

    def run_model(self, model, train_loader, valid_loader, criterion, metric=None, lr=0.01, epochs=10):
        x0 = time.time()
        optim = torch.optim.SGD(model.parameters(), lr=lr, momentum=0.9, weight_decay=1e-5)
        x1 = time.time()
        for epoch in range(1, epochs + 1):
            x2 = time.time()
            self.train(model, criterion, metric, train_loader, optim, epoch)
            # self.validate(model, criterion,  metric, valid_loader)
            x3 = time.time()
        print("TIme for complete function: ", x3-x0)
        print("Time for optim : ", x1-x0)
        print("Time for train: ",x3-x1 )
        print("Time for train: ",x3-x2 )
